import React, { useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  useMapEvents,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";

// Componente auxiliar para capturar los clics en el mapa
function ClickHandler({ onLocationSelected }) {
  useMapEvents({
    click(e) {
      onLocationSelected(e.latlng);
    },
  });
  return null;
}

export default function MapaInteractivo({ onSeleccion }) {
  const [posicion, setPosicion] = useState(null);
  // Coordenadas iniciales (Valparaíso / Viña del Mar)
  const centroInicial = [-33.0456, -71.6197];

  const manejarSeleccion = (latlng) => {
    setPosicion(latlng);
    if (onSeleccion) {
      // Pasamos un nombre genérico de zona basado en coordenadas para el backend
      onSeleccion(
        `Zona Lat: ${latlng.lat.toFixed(3)}, Lng: ${latlng.lng.toFixed(3)}`,
      );
    }
  };

  return (
    <div
      style={{
        height: "400px",
        width: "100%",
        borderRadius: "8px",
        overflow: "hidden",
      }}
    >
      <MapContainer
        center={centroInicial}
        zoom={10}
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <ClickHandler onLocationSelected={manejarSeleccion} />

        {posicion && (
          <Marker position={posicion}>
            <Popup>
              Zona seleccionada <br />
              Lat: {posicion.lat.toFixed(4)} <br />
              Lng: {posicion.lng.toFixed(4)}
            </Popup>
          </Marker>
        )}
      </MapContainer>
    </div>
  );
}
