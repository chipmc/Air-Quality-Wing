#!/usr/bin/env python3
"""Read-only, standard-library PM2.5 display; compatible with Python 3.7+."""
import argparse
from datetime import datetime, timedelta, timezone
import getpass
import json
import math
import os
from pathlib import Path
import queue
import re
import subprocess
import tempfile
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

CONFIG_PATH = Path.home() / '.config' / 'air-quality-display' / 'config.json'
DEFAULT_DEVICE = 'e00fce6889936b9d0ffd8930'
API = 'https://industrial.api.ubidots.com/api/v1.6/devices/'
SGT = timezone(timedelta(hours=8), 'SGT')
PANELS = [('INDOOR', 'pm25', 40 * 60), ('OUTDOOR', 'outdoor_pm25_1h', 90 * 60)]
BG = '#101820'
GREY = '#aab4be'


class DisplayError(Exception):
    """Only fixed messages suitable for the screen; never raw network exceptions."""


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_config(path=CONFIG_PATH):
    try:
        if os.name == 'posix' and path.stat().st_mode & 0o077:
            raise DisplayError('Config must be private: chmod 600 your config file')
        if path.stat().st_size > 8192:
            raise DisplayError('Invalid configuration')
        config = json.loads(path.read_text())
    except (OSError, ValueError):
        raise DisplayError('Run with --configure first') from None
    if not isinstance(config, dict):
        raise DisplayError('Invalid configuration')
    token = config.get('token')
    device = config.get('device')
    if (not isinstance(token, str) or not token.strip() or any(c.isspace() for c in token)
            or not isinstance(device, str) or not re.fullmatch(r'[a-zA-Z0-9_-]+', device)):
        raise DisplayError('Invalid configuration')
    return config


def configure(path=CONFIG_PATH):
    device = input('Ubidots device API label [{}]: '.format(DEFAULT_DEVICE)).strip() or DEFAULT_DEVICE
    token = getpass.getpass('Ubidots API token (hidden; preferably read-only/device-scoped): ').strip()
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', device) or not token or any(c.isspace() for c in token):
        raise DisplayError('Invalid device label or token; configuration not saved')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(dir=str(path.parent), prefix='.config-')
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump({'device': device, 'token': token}, stream)
        os.replace(name, str(path))
    finally:
        if os.path.exists(name):
            os.unlink(name)
    print('Private configuration saved outside the project. No token displayed.')


def fetch(config, variable, params):
    url = API + quote(config['device'], safe='') + '/' + quote(variable, safe='') + '/values/?' + urlencode(params)
    request = Request(url, headers={'X-Auth-Token': config['token'], 'Accept': 'application/json',
                                   'User-Agent': 'Air-Quality-Wing-Display/1.0'}, method='GET')
    try:
        with build_opener(NoRedirects()).open(request, timeout=8) as response:
            raw = response.read(65537)
    except HTTPError as error:
        status = error.code
        error.close()
        raise DisplayError('HTTP {}'.format(status if type(status) is int else 'error')) from None
    except (URLError, OSError, ValueError):
        raise DisplayError('Connection failed') from None
    if len(raw) > 65536:
        raise DisplayError('Response too large')
    try:
        return json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise DisplayError('Invalid server response') from None


def latest_dot(payload, now):
    if not isinstance(payload, dict) or not isinstance(payload.get('results'), list):
        raise DisplayError('Invalid server response')
    if not payload['results']:
        return None
    # Latest null/invalid data must not silently fall back to a previous valid dot.
    dots = payload['results']
    for dot in dots:
        if not isinstance(dot, dict) or type(dot.get('timestamp')) not in (int, float):
            raise DisplayError('Invalid observation')
        ts = dot['timestamp']
        if not math.isfinite(ts) or ts <= 0 or ts > (now + 300) * 1000:
            raise DisplayError('Invalid observation time')
    dot = max(dots, key=lambda item: item['timestamp'])
    value = dot.get('value')
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise DisplayError('Latest reading unavailable')
    return {'value': value, 'timestamp': dot['timestamp']}


def fetch_panel(config, variable, now, request=fetch):
    dot = latest_dot(request(config, variable, {'page_size': 1}), now)
    if dot is None:
        return {'dot': None, 'baseline': None, 'error': ''}
    # Compare with the latest observation at/before one hour before this dot.
    target = dot['timestamp'] - 3600000
    baseline = None
    try:
        baseline = latest_dot(request(config, variable, {
            'page_size': 1, 'start': int(target - 900000), 'end': int(target)}), now)
        if baseline and not target - 900000 <= baseline['timestamp'] <= target:
            baseline = None
    except DisplayError:
        pass  # Current value can still be shown; do not invent a trend.
    return {'dot': dot, 'baseline': baseline, 'error': ''}


def band(value, outdoor):
    # Outdoor NEA one-hour bands. Indoor uses these ranges only as an indicative scale.
    labels = ['Normal', 'Elevated', 'High', 'Very high'] if outdoor else [
        'Range 0–55', 'Range >55–150', 'Range >150–250', 'Range >250']
    colors = ['#7ee787', '#80caff', '#ffbf69', '#ff7b86']
    index = 0 if value <= 55 else 1 if value <= 150 else 2 if value <= 250 else 3
    return labels[index], colors[index]


def trend(dot, baseline):
    if not baseline:
        return '—', '1h trend unavailable'
    target = dot['timestamp'] - 3600000
    if not target - 900000 <= baseline['timestamp'] <= target:
        return '—', '1h trend unavailable'
    delta = dot['value'] - baseline['value']
    # An explicit 2 ug/m3 deadband prevents a one-unit change dominating the display.
    arrow = '↑' if delta > 2 else '↓' if delta < -2 else '→'
    return arrow, '{:+.0f} µg/m³ vs ~1h ago'.format(delta)


def panel_text(snapshot, now, outdoor, stale_after):
    dot = snapshot.get('dot')
    error = snapshot.get('error', '')
    if not dot:
        return ['--', '—', 'OFFLINE' if error else 'NO DATA', 'Waiting for a valid reading',
                error or 'No observations returned', GREY]
    age = max(0, now - dot['timestamp'] / 1000)
    label, color = band(dot['value'], outdoor)
    arrow, delta = trend(dot, snapshot.get('baseline'))
    if error or age > stale_after:
        label, color, arrow, delta = ('OFFLINE' if error else 'STALE'), GREY, '—', 'Trend paused'
    stamp = datetime.fromtimestamp(dot['timestamp'] / 1000, SGT).strftime('%d %b %H:%M SGT')
    return ['{:g}'.format(dot['value']), arrow, label, delta,
            'Observed {} • {} min old'.format(stamp, int(age / 60)), color]


def keep_screen_awake():
    """Apply X11 settings without shell interpolation or privileged configuration."""
    for args in [('s', 'off'), ('s', 'noblank'), ('-dpms',), ('s', 'reset')]:
        try:
            subprocess.run(['xset'] + list(args), stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=3, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return False
    return True


def run_gui(config, demo=False, windowed=False, keep_awake=False):
    import tkinter as tk
    from tkinter import font as tkfont
    root = tk.Tk()
    root.title('Singapore Air Quality')
    root.configure(bg=BG)
    root.geometry('1280x720')
    root.attributes('-fullscreen', not windowed)
    root.bind('<Escape>', lambda event: root.destroy())
    root.bind('<F11>', lambda event: root.attributes('-fullscreen', not root.attributes('-fullscreen')))
    tk.Label(root, text='SINGAPORE  •  PM2.5' + ('  •  DEMO' if demo else ''),
             bg=BG, fg='white', font=('DejaVu Sans', 22, 'bold')).pack(pady=8)
    body = tk.Frame(root, bg=BG)
    body.pack(fill='both', expand=True)
    body.rowconfigure(0, weight=1)
    widgets = []
    reading_layouts = []
    number_font = tkfont.Font(family='DejaVu Sans', size=160, weight='bold')
    for index, (title, variable, stale) in enumerate(PANELS):
        body.columnconfigure(index, weight=1, uniform='panel')
        frame = tk.Frame(body, bg=BG, highlightbackground='#394957', highlightthickness=1)
        frame.grid(row=0, column=index, sticky='nsew', padx=8, pady=4)
        subtitle = 'Latest sensor reading • indicative colours' if index == 0 else 'NEA Central • one-hour average'
        for text, size in [(title, 28), (subtitle, 16)]:
            tk.Label(frame, text=text, bg=BG, fg='white', font=('DejaVu Sans', size)).pack(pady=5)
        reading = tk.Frame(frame, bg=BG)
        reading.pack(expand=True)
        value = tk.Label(reading, text='--', bg=BG, fg=GREY, font=number_font)
        value.pack(side='left')
        units = tk.Label(reading, text='µg/m³', bg=BG, fg=GREY, font=('DejaVu Sans', 20))
        units.pack(side='left', anchor='s', padx=(8, 0), pady=(0, 12))
        reading_layouts.append((frame, units))
        arrow = tk.Label(frame, text='—', bg=BG, fg=GREY, font=('DejaVu Sans', 60, 'bold'))
        arrow.pack()
        labels = []
        for size in (25, 20, 16):
            widget = tk.Label(frame, text='', bg=BG, fg=GREY, font=('DejaVu Sans', size))
            widget.pack(pady=4)
            labels.append(widget)
        widgets.append((value, arrow, labels))
    status = tk.Label(root, bg=BG, fg=GREY, font=('DejaVu Sans', 16))
    status.pack(pady=6)
    pending = queue.Queue()
    snapshots = [{'dot': None, 'baseline': None, 'error': ''} for unused in PANELS]

    def worker():
        result = []
        now = time.time()
        for index, (unused, variable, stale) in enumerate(PANELS):
            if demo:
                result.append({'dot': {'value': [26, 205][index], 'timestamp': now * 1000},
                               'baseline': {'value': [32, 180][index], 'timestamp': (now - 3600) * 1000},
                               'error': ''})
                continue
            try:
                result.append(fetch_panel(config, variable, now))
            except DisplayError as error:
                result.append({'error': str(error)})
            except Exception:
                result.append({'error': 'Read failed'})
        pending.put(result)

    def poll():
        threading.Thread(target=worker, daemon=True).start()
        root.after(300000, poll)  # Four small GETs per five minutes; no data writes.

    def fit_numbers(event=None):
        if event is not None and event.widget != root:
            return
        # Keep both readings equally large; fit even four-digit observations.
        if min(frame.winfo_width() for frame, units in reading_layouts) <= 1:
            return
        size = max(36, min(170, int(root.winfo_width() * .125)))
        probe = tkfont.Font(family='DejaVu Sans', size=size, weight='bold')
        while size > 36:
            fits = all(probe.measure(str(widgets[i][0].cget('text'))) + 8
                       <= frame.winfo_width() - units.winfo_reqwidth() - 40
                       for i, (frame, units) in enumerate(reading_layouts))
            if fits:
                break
            size -= 1
            probe.configure(size=size)
        if number_font.cget('size') != size:
            number_font.configure(size=size)

    def redraw():
        try:
            result = pending.get_nowait()
            for index, item in enumerate(result):
                if 'dot' not in item:
                    snapshots[index]['error'] = item['error']
                else:
                    snapshots[index] = item
        except queue.Empty:
            pass
        now = time.time()
        for index, (unused, variable, stale) in enumerate(PANELS):
            value, arrow, band_label, delta, stamp, color = panel_text(snapshots[index], now, index == 1, stale)
            value_widget, arrow_widget, labels = widgets[index]
            value_widget.configure(text=value, fg=color)
            arrow_widget.configure(text=arrow, fg=color)
            for widget, text in zip(labels, (band_label, delta, stamp)):
                widget.configure(text=text, fg=color)
        fit_numbers()
        clock = datetime.now(SGT).strftime('%d %b %Y  %H:%M:%S SGT')
        state = ' • read error; retrying' if any(s.get('error') for s in snapshots) else ''
        status.configure(text=clock + '  •  refresh 5 min  •  Esc to exit' + state)
        root.after(1000, redraw)

    root.bind('<Configure>', fit_numbers)
    def awake_tick():
        keep_screen_awake()
        root.after(60000, awake_tick)

    if keep_awake:
        awake_tick()
    poll()
    redraw()
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configure', action='store_true')
    parser.add_argument('--demo', action='store_true', help='Invented values; no network or credentials')
    parser.add_argument('--windowed', action='store_true')
    parser.add_argument('--keep-awake', action='store_true', help='Keep the X11 screen on while the app runs')
    parser.add_argument('--check', action='store_true', help='Read API once without opening a window')
    args = parser.parse_args()
    try:
        if args.configure:
            configure()
            return 0
        config = None if args.demo else read_config()
        if args.check:
            if args.demo:
                raise DisplayError('Use --demo without --check')
            for title, variable, stale in PANELS:
                result = fetch_panel(config, variable, time.time())
                print(title + ': ' + ' | '.join(panel_text(result, time.time(), title == 'OUTDOOR', stale)[:5]))
            return 0
        run_gui(config, args.demo, args.windowed, args.keep_awake)
        return 0
    except DisplayError as error:
        print(str(error))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
