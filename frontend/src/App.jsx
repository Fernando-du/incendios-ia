import { useState } from 'react'
import MapaInteractivo from './components/MapaInteractivo'
import DashboardPredictor from './components/DashboardPredictor'
import './App.css'

function App() {
  // Estado global para compartir la zona entre el mapa y el dashboard
  const [zonaSeleccionada, setZonaSeleccionada] = useState("")

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '20px', fontFamily: 'sans-serif' }}>
      
      <header style={{ textAlign: 'center', marginBottom: '30px' }}>
        <h1 style={{ color: '#d9534f', margin: '0 0 10px 0' }}>
          🔥 Sistema Predictivo de Incendios Forestales
        </h1>
        <p style={{ color: '#555', fontSize: '1.1rem' }}>
          Selecciona una zona en el mapa y evalúa el riesgo utilizando Inteligencia Artificial.
        </p>
      </header>

      <main style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', 
        gap: '30px' 
      }}>
        
        {/* Columna Izquierda: Mapa */}
        <section>
          <h2 style={{ borderBottom: '2px solid #ddd', paddingBottom: '10px' }}>
            1. Selecciona la Ubicación
          </h2>
          <MapaInteractivo onSeleccion={setZonaSeleccionada} />
        </section>

        {/* Columna Derecha: Dashboard y Formulario */}
        <section>
          <h2 style={{ borderBottom: '2px solid #ddd', paddingBottom: '10px' }}>
            2. Evaluación de Riesgo
          </h2>
          <DashboardPredictor zonaSeleccionada={zonaSeleccionada} />
        </section>

      </main>

    </div>
  )
}

export default App