import React, { useState } from "react";

export default function DashboardPredictor({ zonaSeleccionada }) {
  const [datos, setDatos] = useState({
    temperatura: 30,
    humedad: 40,
    viento: 25,
    vegetacion: 60,
    incendios_historicos: 2,
  });

  const [resultado, setResultado] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);

  const manejarCambio = (e) => {
    setDatos({
      ...datos,
      [e.target.name]: parseFloat(e.target.value) || 0,
    });
  };

  const evaluarRiesgo = async () => {
    if (!zonaSeleccionada) {
      setError("Por favor, selecciona una zona en el mapa primero.");
      return;
    }

    setCargando(true);
    setError(null);
    setResultado(null);

    try {
      // Nginx redirigirá esta ruta al contenedor api-riesgo
      const respuesta = await fetch("/api/v1/riesgo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          zona: zonaSeleccionada,
          ...datos,
        }),
      });

      const data = await respuesta.json();

      if (!respuesta.ok) {
        throw new Error(data.detail || "Error al conectar con la API");
      }

      setResultado(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  };

  return (
    <div
      style={{
        padding: "20px",
        border: "1px solid #ddd",
        borderRadius: "8px",
        backgroundColor: "#f9f9f9",
      }}
    >
      <h3>Dashboard Predictivo</h3>
      <p>
        <strong>Zona Actual:</strong>{" "}
        {zonaSeleccionada || "Ninguna (clic en el mapa)"}
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "15px",
          marginBottom: "20px",
        }}
      >
        <div>
          <label>Temperatura (°C): </label>
          <input
            type="number"
            name="temperatura"
            value={datos.temperatura}
            onChange={manejarCambio}
            style={{ width: "100%" }}
          />
        </div>
        <div>
          <label>Humedad (%): </label>
          <input
            type="number"
            name="humedad"
            value={datos.humedad}
            onChange={manejarCambio}
            style={{ width: "100%" }}
          />
        </div>
        <div>
          <label>Viento (km/h): </label>
          <input
            type="number"
            name="viento"
            value={datos.viento}
            onChange={manejarCambio}
            style={{ width: "100%" }}
          />
        </div>
        <div>
          <label>Vegetación seca (%): </label>
          <input
            type="number"
            name="vegetacion"
            value={datos.vegetacion}
            onChange={manejarCambio}
            style={{ width: "100%" }}
          />
        </div>
        <div style={{ gridColumn: "span 2" }}>
          <label>Incendios Históricos: </label>
          <input
            type="number"
            name="incendios_historicos"
            value={datos.incendios_historicos}
            onChange={manejarCambio}
            style={{ width: "100%" }}
          />
        </div>
      </div>

      <button
        onClick={evaluarRiesgo}
        disabled={cargando}
        style={{
          padding: "10px 20px",
          backgroundColor: "#007bff",
          color: "white",
          border: "none",
          borderRadius: "4px",
          cursor: "pointer",
          width: "100%",
        }}
      >
        {cargando ? "Evaluando..." : "Calcular Riesgo"}
      </button>

      {error && <p style={{ color: "red", marginTop: "15px" }}>{error}</p>}

      {resultado && (
        <div
          style={{
            marginTop: "20px",
            padding: "15px",
            backgroundColor: "white",
            borderRadius: "4px",
            borderLeft: `5px solid ${resultado.riesgo === "ALTO" ? "red" : resultado.riesgo === "MEDIO" ? "orange" : "green"}`,
          }}
        >
          <h4 style={{ margin: "0 0 10px 0" }}>
            Nivel de Riesgo: {resultado.riesgo}
          </h4>
          <p style={{ margin: "5px 0" }}>
            <strong>Probabilidades:</strong>
          </p>
          <ul style={{ margin: "5px 0 15px 0", paddingLeft: "20px" }}>
            <li>BAJO: {(resultado.probabilidades.BAJO * 100).toFixed(1)}%</li>
            <li>MEDIO: {(resultado.probabilidades.MEDIO * 100).toFixed(1)}%</li>
            <li>ALTO: {(resultado.probabilidades.ALTO * 100).toFixed(1)}%</li>
          </ul>
          <small style={{ color: "#666" }}>{resultado.advertencia}</small>
        </div>
      )}
    </div>
  );
}
