import React, { useState, useEffect } from "react";

export default function DashboardPredictor({ zonaSeleccionada }) {
  const [estacionesReales, setEstacionesReales] = useState([]);
  const [estacionActiva, setEstacionActiva] = useState("");

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

  // 1. Cargar observaciones reales desde PostgreSQL al iniciar el dashboard
  useEffect(() => {
    const cargarEstaciones = async () => {
      try {
        const res = await fetch("/api/v1/observaciones/ultimas");
        if (res.ok) {
          const lista = await res.json();
          setEstacionesReales(lista);
        }
      } catch (err) {
        console.error("No se pudieron cargar estaciones desde PostgreSQL:", err);
      }
    };
    cargarEstaciones();
  }, []);

  // 2. Autocompletar variables reales al seleccionar una estación de la BD
  const seleccionarEstacionReal = (e) => {
    const nombreZona = e.target.value;
    setEstacionActiva(nombreZona);
    setResultado(null);
    setError(null);

    const encontrada = estacionesReales.find((item) => item.zona === nombreZona);
    if (encontrada) {
      setDatos({
        temperatura: encontrada.temperatura,
        humedad: encontrada.humedad,
        viento: encontrada.viento,
        vegetacion: encontrada.vegetacion,
        incendios_historicos: encontrada.incendios_historicos,
      });
    }
  };

  const manejarCambio = (e) => {
    setDatos({
      ...datos,
      [e.target.name]: parseFloat(e.target.value) || 0,
    });
  };

  // Usar la estación real elegida o el punto marcado en el mapa
  const zonaFinal = estacionActiva || zonaSeleccionada;

  const evaluarRiesgo = async () => {
    if (!zonaFinal) {
      setError("Selecciona una estación real de la lista o haz clic en el mapa.");
      return;
    }

    setCargando(true);
    setError(null);
    setResultado(null);

    try {
      const respuesta = await fetch("/api/v1/riesgo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          zona: zonaFinal,
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

      {/* Selector de Estaciones Reales (EMAS + CONAF desde PostgreSQL) */}
      <div style={{ marginBottom: "15px" }}>
        <label style={{ display: "block", fontWeight: "bold", marginBottom: "5px" }}>
          Cargar Datos Reales (Estaciones EMAS / CONAF):
        </label>
        <select
          value={estacionActiva}
          onChange={seleccionarEstacionReal}
          style={{
            width: "100%",
            padding: "8px",
            borderRadius: "4px",
            border: "1px solid #ccc",
            backgroundColor: "white",
          }}
        >
          <option value="">
            {estacionesReales.length > 0
              ? "-- Selecciona una estación con datos reales --"
              : "-- Sin datos en BD (sube dataset_real_unificado.csv primero) --"}
          </option>
          {estacionesReales.map((est, idx) => (
            <option key={idx} value={est.zona}>
              {est.zona} (Temp: {est.temperatura}°C | Hum: {est.humedad}%)
            </option>
          ))}
        </select>
      </div>

      <p>
        <strong>Zona a Evaluar:</strong>{" "}
        {zonaFinal || "Ninguna (elige estación o clic en mapa)"}
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
            borderLeft: `5px solid ${
              resultado.riesgo === "ALTO"
                ? "red"
                : resultado.riesgo === "MEDIO"
                ? "orange"
                : "green"
            }`,
          }}
        >
          <h4 style={{ margin: "0 0 10px 0" }}>
            Nivel de Riesgo: {resultado.riesgo}
          </h4>
          <p style={{ margin: "5px 0" }}>
            <strong>Probabilidades:</strong>
          </p>
          <ul style={{ margin: "5px 0 15px 0", paddingLeft: "20px" }}>
            <li>BAJO: {((resultado.probabilidades.BAJO || 0) * 100).toFixed(1)}%</li>
            <li>MEDIO: {((resultado.probabilidades.MEDIO || 0) * 100).toFixed(1)}%</li>
            <li>ALTO: {((resultado.probabilidades.ALTO || 0) * 100).toFixed(1)}%</li>
          </ul>
          <small style={{ color: "#666" }}>Modelo: {resultado.modelo}</small>
        </div>
      )}
    </div>
  );
}