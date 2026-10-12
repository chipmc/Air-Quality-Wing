# Particle `air_quality` → Ubidots

## Existing integration and evidence

The owner reports the seven measurements updating in Ubidots through a Particle
webhook. This repository contains firmware, not an export of the owner's live
webhook settings. The configuration below reproduces the documented routing
pattern; the current Ubidots API device label, device filter and secret binding
must be checked by the owner in the consoles. No live integration was changed by
this documentation update. Do not rename an existing API label accidentally;
a dashboard display name can be changed independently.

## Event contract

The firmware calls `Particle.publish("air_quality", payload)` when connected.
Event data is a JSON object, not a JSON string nested in a second `data` object.
An illustrative payload after conditioning is:

```json
{"pm25":12,"pm10":21,"temperature":25.40,"humidity":61.20,"tvoc":85,"eco2":620,"rssi":-58}
```

| JSON key / Ubidots variable label | Numeric meaning | Firmware acceptance |
| --- | --- | --- |
| `pm25` | PM2.5, µg/m³ | Integer 0–1000 |
| `pm10` | PM10, µg/m³ | Integer 0–1000 |
| `temperature` | °C | Finite −40–125, two decimals in JSON |
| `humidity` | %RH | Finite 0–100, two decimals in JSON |
| `tvoc` | ppb | Integer 0–32768 |
| `eco2` | Estimated equivalent CO₂, ppm | Integer 400–29206 |
| `rssi` | Wi-Fi signal, dBm | Negative number when Wi-Fi is ready |

All seven keys are present, with a number or literal JSON `null`. These are
software validity bounds, not an accuracy guarantee or air quality classification.
Sensor fields expire at 10 seconds. PM and environment pairs share validity;
VOC fields also require the firmware's 20-minute conditioning gate. RSSI is null
when Wi-Fi is unavailable or RSSI is zero/positive. The first report waits for
startup; subsequent reports are 60 seconds apart. Offline reports are dropped.
No sample timestamp is included; Particle's event metadata supplies publish time.

## Configure a webhook without exposing credentials

1. In Particle Console, select the correct sandbox/organization and create a
   Cloud Secret named `UBIDOTS_TOKEN`. Enter the credential only in the secure
   secret editor. Limit its Ubidots permissions to the required ingestion scope
   where available. Do not save its value in the repository or event payload.
2. Create or edit the webhook for event `air_quality`, scoped to the owner's
   Argon device. Particle event filters match prefixes; verify the event name
   and avoid overlapping names or duplicate webhooks that write twice.
3. Use HTTP **POST**, **Custom Body**, and disable **Include Default Data**.
   For a new per-device mapping, the URL is:

   ```text
   https://industrial.api.ubidots.com/api/v1.6/devices/{{{PARTICLE_DEVICE_ID}}}
   ```

   For the existing monitor, keep its current API label in the URL instead if
   that is how the working webhook routes data. Device IDs and API labels are
   routing identifiers; a display name is not necessarily the API label.
4. Enable the `UBIDOTS_TOKEN` secret for this integration. Set HTTP headers:

   | Header | Value entered in the webhook |
   | --- | --- |
   | `Content-Type` | `application/json` |
   | `X-Auth-Token` | `{{{UBIDOTS_TOKEN}}}` |

   The template is a secret reference, not a token value. If Cloud Secrets are
   unavailable in the selected scope, resolve that with the owner before setup;
   do not substitute a credential into a committed configuration.
5. Set the custom body to exactly:

   ```text
   {{{PARTICLE_EVENT_VALUE}}}
   ```

   Triple braces forward the event JSON without HTML escaping. Do not surround
   the expression with quotes and do not map each field through an unguarded
   numeric substitution: `null` fields can turn into empty/invalid JSON.
6. Save, then verify delivery using the checklist below. Configure variable
   units in Ubidots to match the table above. No Ubidots firmware library,
   Particle account token or GitHub secret is needed for this webhook pattern.

## Missing values and delivery verification

`null` means unavailable, not zero. The owner-reported successful numeric readings
do not establish how the live Ubidots endpoint handles every null-containing
payload. Test that behavior explicitly; do not claim Ubidots stores a null dot.
Check the response for each variable as well as the overall HTTP result.

- Test the numeric example and confirm all seven variable labels, units, values
  and new timestamps in the intended Ubidots device.
- Test `tvoc`/`eco2` null during startup and mixed-null/missing-sensor payloads.
  Confirm numeric fields still update. Inspect webhook errors and the response
  body for rejected variables or batches.
- If the endpoint rejects null-containing data, an owner-approved cloud adapter
  can omit null keys while retaining numeric zero. If every field is null, skip
  ingestion. Keep the device's JSON contract unchanged. Such an adapter is an
  optional extension, not an implemented feature of this repository.
- When a variable is omitted/rejected its previous dot may remain visible.
  Dashboards must use timestamps to show stale/unavailable values; never present
  the previous dot as a fresh reading or replace missing values with zero.
- Check Particle Console's event stream, webhook logs and Ubidots timestamps.
  “Publish accepted” confirms API acceptance only. A webhook success must still
  be checked against per-variable results. Check authentication, label routing,
  quotas and response bodies if data is absent. Redact exported logs.
- Disable Wi-Fi and confirm local reporting continues with publishing skipped.
  Reconnect and verify current reports resume; there is no device backlog replay.

The backend stores server reception time unless an adapter adds an explicit
Ubidots timestamp. Do not label that time as a precision sensor acquisition time.
For new integrations, account for possible cloud retries/duplicates and monitor
staleness separately from the firmware's sensor freshness gate.

## Primary documentation

- [Particle webhook reference and Cloud Secrets](https://docs.particle.io/reference/cloud-apis/webhooks/)
- [Particle JSON and webhook templates](https://docs.particle.io/firmware/best-practices/json/)
- [Ubidots Particle webhook guide](https://help.ubidots.com/en/articles/513304-connect-your-particle-device-to-ubidots-using-particle-webhooks)

Use the routing pattern from those guides with this project's existing publisher;
do not copy unrelated example firmware or add device-side credentials.
