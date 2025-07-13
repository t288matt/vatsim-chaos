# Animation

This directory contains the 3D animation visualization for the ATC Conflict Analysis System.

## Cesium Flight Animation

- **File:** `cesium_flight_anim.html`
- **Description:**
  - Standalone HTML file for animated 3D globe flight visualization using CesiumJS (Google Earth style).
  - No Node.js or build tools required. Just open in your browser.
  - **Shows all flights** with their scheduled departure times to create planned conflicts.
- **How to use:**
  1. Open `cesium_flight_anim.html` in your browser (Chrome, Edge, or Firefox).
  2. You will see a 3D globe with animated flights departing at their scheduled times.
  3. The visualization automatically loads the latest analysis data.
  4. Use the timeline controls to play/pause the animation.
  5. Real-time conflict alerts appear when conflicts occur.

## Customization

- **Aircraft Icon Size**: Adjust `minimumPixelSize` and `maximumScale` in the `model` property in `cesium_flight_anim.html`.
- **Label Position/Size**: Change `pixelOffset` and `font` in the `label` property for each flight entity.
- **Real-Time Altitude**: Labels update live as aircraft move.
- **Conflict Alerts**: Red markers and alerts appear when conflicts occur.
- **Camera Auto-Zoom**: Automatically zooms to fit all flights at start.

## Data Files

- `animation_data.json` - Complete flight and conflict data for visualization
- `flight_tracks.json` - Individual flight path data
- `conflict_points.json` - Conflict location and timing data

## Refreshing Data

- After running `generate_animation.py`, reload `cesium_flight_anim.html` in your browser to see updated flights/conflicts.

## Troubleshooting

- If no flights appear, ensure `animation_data.json` is present and up to date.
- For large icons or overlapping labels, adjust `minimumPixelSize`, `maximumScale`, `font`, and `pixelOffset` in the HTML.

## Features

- **Real-time Conflicts**: Conflict points marked on the globe
- **Live Alerts**: Conflict warnings appear during animation
- **3D Navigation**: Zoom, pan, and rotate around the globe
- **Timeline Control**: Full animation timeline with play/pause/speed controls

---

For help with data generation or customization, run the analysis scripts in the main directory. 