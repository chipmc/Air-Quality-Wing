import importlib.util
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

spec = importlib.util.spec_from_file_location('display_app', Path(__file__).resolve().parents[1] / 'air_quality_display.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
NOW = 1792058400


def dot(value=26, age=0):
    return {'value': value, 'timestamp': (NOW - age) * 1000}


class DisplayTests(unittest.TestCase):
    def test_zero_is_valid_but_null_negative_bool_nonfinite_are_not(self):
        self.assertEqual(m.latest_dot({'results': [dot(0)]}, NOW)['value'], 0)
        for value in (None, True, -1, float('nan'), float('inf'), '20'):
            with self.subTest(value=value), self.assertRaises(m.DisplayError):
                m.latest_dot({'results': [dot(value)]}, NOW)

    def test_invalid_latest_never_falls_back(self):
        with self.assertRaises(m.DisplayError):
            m.latest_dot({'results': [dot(None), dot(12, 60)]}, NOW)

    def test_bad_or_future_timestamps_rejected(self):
        for ts in (0, True, '123', float('nan'), (NOW + 301) * 1000):
            with self.assertRaises(m.DisplayError):
                m.latest_dot({'results': [{'value': 20, 'timestamp': ts}]}, NOW)

    def test_hour_baseline_query_is_small_and_relative_to_observation(self):
        requests = []
        def request(config, variable, params):
            requests.append(params)
            return {'results': [dot(26, 600) if len(requests) == 1 else dot(32, 4200)]}
        result = m.fetch_panel({}, 'pm25', NOW, request)
        self.assertEqual(requests[0], {'page_size': 1})
        self.assertEqual(requests[1]['end'], (NOW - 4200) * 1000)
        self.assertEqual(m.trend(result['dot'], result['baseline'])[0], '↓')

    def test_missing_history_and_nearby_invalid_baseline_have_no_trend(self):
        self.assertEqual(m.trend(dot(), None)[0], '—')
        self.assertEqual(m.trend(dot(), dot(30, 7200))[0], '—')
        self.assertEqual(m.trend(dot(), dot(30, 3500))[0], '—')

    def test_trend_deadband_and_directions(self):
        for old, arrow in [(20, '↑'), (32, '↓'), (24, '→'), (28, '→')]:
            self.assertEqual(m.trend(dot(), dot(old, 3600))[0], arrow)

    def test_stale_and_offline_values_are_grey_and_have_no_arrow(self):
        for snapshot in [{'dot': dot(age=2500), 'baseline': dot(30, 6100)},
                         {'dot': dot(), 'baseline': dot(30, 3600), 'error': 'HTTP 403'}]:
            result = m.panel_text(snapshot, NOW, False, 2400)
            self.assertEqual(result[1], '—')
            self.assertEqual(result[-1], m.GREY)
        self.assertEqual(m.panel_text({'dot': dot(age=5000)}, NOW, True, 5400)[2], 'Normal')

    def test_timestamp_displays_singapore_and_does_not_change_stored_instant(self):
        self.assertIn('15 Oct 18:00 SGT', m.panel_text({'dot': dot()}, NOW, True, 5400)[4])

    def test_indoor_colours_are_ranges_not_official_health_categories(self):
        for value, expected in [(0, 'Normal'), (55, 'Normal'), (56, 'Elevated'),
                                (150, 'Elevated'), (151, 'High'), (250, 'High'), (251, 'Very high')]:
            self.assertEqual(m.band(value, True)[0], expected)
            self.assertTrue(m.band(value, False)[0].startswith('Range'))

    def test_empty_or_failed_baseline_does_not_hide_current_value(self):
        replies = iter([{'results': [dot()]}, m.DisplayError('HTTP 503')])
        def request(*args):
            reply = next(replies)
            if isinstance(reply, Exception): raise reply
            return reply
        self.assertIsNone(m.fetch_panel({}, 'pm25', NOW, request)['baseline'])
        self.assertIsNone(m.latest_dot({'results': []}, NOW))

    def test_requests_are_get_fixed_host_and_header_auth_no_redirects(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"results": []}'
        opener = MagicMock()
        opener.open.return_value = response
        with patch.object(m, 'build_opener', return_value=opener):
            m.fetch({'device': 'monitor', 'token': 'PRIVATE'}, 'pm25', {'page_size': 1})
        request = opener.open.call_args[0][0]
        self.assertEqual(request.get_method(), 'GET')
        self.assertTrue(request.full_url.startswith(m.API))
        self.assertNotIn('PRIVATE', request.full_url)
        self.assertEqual(request.get_header('X-auth-token'), 'PRIVATE')
        self.assertIsNone(m.NoRedirects().redirect_request(None, None, 302, '', {}, 'https://other.example'))

    def test_network_errors_do_not_expose_credentials(self):
        opener = MagicMock()
        opener.open.side_effect = HTTPError(m.API, 403, 'PRIVATE', {}, io.BytesIO(b'PRIVATE'))
        with patch.object(m, 'build_opener', return_value=opener), self.assertRaisesRegex(m.DisplayError, '^HTTP 403$'):
            m.fetch({'device': 'monitor', 'token': 'PRIVATE'}, 'pm25', {})

    def test_config_is_private_and_does_not_echo_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'private' / 'config.json'
            with patch('builtins.input', return_value='monitor'), patch.object(m.getpass, 'getpass', return_value='PRIVATE'), patch('builtins.print') as output:
                m.configure(path)
            self.assertNotIn('PRIVATE', str(output.call_args_list))
            self.assertEqual(m.read_config(path)['device'], 'monitor')
            if os.name == 'posix':
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                path.chmod(0o644)
                with self.assertRaises(m.DisplayError): m.read_config(path)


if __name__ == '__main__': unittest.main()
