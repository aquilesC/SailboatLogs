# Maps in Sailboat Logs

When working with Leaflet maps in this project, adhere to the following approaches (as seen in `trip_detail_internal.html`):

1. **Tile Layer**: Use the CartoDB Voyager tiles for a clean, maritime-friendly look.
   ```javascript
   L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
     attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
     maxZoom: 19,
     subdomains: 'abcd',
   }).addTo(map);
   ```

2. **Styling**: Ensure the map container has a defined height and a lower `z-index` so it doesn't overlap navigation dropdowns.
   ```css
   #map-container { height: 400px; border-radius: 0.75rem; z-index: 0; }
   @media (min-width: 1024px) { #map-container { height: 500px; } }
   ```

3. **Visibility & Sizing**: If the map container starts with `display: none` (e.g. using Tailwind's `hidden` class), Leaflet cannot determine the dimensions of the map when initializing. This leads to the map appearing "blocked" or only showing a single tile in the corner. Always call `map.invalidateSize()` shortly after the container becomes visible.
   ```javascript
   container.classList.remove('hidden');
   setTimeout(() => {
     map.invalidateSize();
   }, 100);
   ```

4. **Fitting Bounds**: After adding points or lines, calculate bounds and apply them with padding.
   ```javascript
   map.fitBounds(allBounds, { padding: [40, 40] });
   ```
