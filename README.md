# 🌲🔥 Sistema Predictivo de Riesgo de Incendios Forestales (Fire Risk Prediction)

Un sistema full-stack modular e impulsado por Inteligencia Artificial diseñado para evaluar el nivel de riesgo de incendios forestales en tiempo real basándose en variables climáticas, características de la vegetación y registros históricos.

---

## 📐 Arquitectura del Sistema

El proyecto está diseñado bajo una arquitectura de microservicios contenerizados y orquestados, compuesta por los siguientes módulos:

* **Frontend:** React 19 + Vite 8 con interfaz interactiva basada en Leaflet para visualización geográfica.
* **API de Riesgo (IA):** FastAPI (Python 3.11) que expone el modelo de Machine Learning (Random Forest / Gradient Boosting) entrenado para predecir niveles de riesgo (BAJO, MEDIO, ALTO).
* **API de Datos:** FastAPI (Python 3.11) encargada de la ingesta, procesamiento y gestión de persistencia.
* **Base de Datos:** PostgreSQL 15 para el almacenamiento relacional de registros e historial de predicciones.
* **Proxy Inverso & Servidor Web:** Nginx actuando como API Gateway y servidor de archivos estáticos del frontend.
* **Orquestación & CI/CD:** Docker Compose, Kubernetes (K8s) y GitHub Actions.

              +-----------------------------------+
              |      Usuario (Navegador Web)     |
              +-----------------------------------+
                                |
                                v (HTTP / Port 80)
              +-----------------------------------+
              |         Nginx Proxy Inverso       |
              +-----------------------------------+
                    /           |           \
                   /            |            \
                  v             v             v
      +---------------+  +--------------+  +--------------+
      | Frontend React|  |  API Riesgo  |  |  API Datos   |
      | (Vite Static) |  | (Modelo IA)  |  |  (FastAPI)   |
      +---------------+  +--------------+  +--------------+
                                                  |
                                                  v
                                           +--------------+
                                           | PostgreSQL 15|
                                           +--------------+

---

## 🛠️ Tecnologías Utilizadas

* **Lenguajes:** JavaScript (ES6+), Python 3.11, SQL.
* **Frontend:** React 19, Vite 8, Leaflet / React-Leaflet, CSS3 / Flexbox / Grid.
* **Backend:** FastAPI, Uvicorn, Pandas, Scikit-learn, SQLAlchemy.
* **Base de Datos:** PostgreSQL 15.
* **DevOps & Infraestructura:** Docker, Docker Compose, Nginx, GitHub Actions (CI/CD), Kubernetes (K8s).

---

## 📂 Estructura del Repositorio

```text
incendios-ia/
├── .github/
│   └── workflows/
│       └── ci.yml             # Pipeline de Integración Continua (GitHub Actions)
├── k8s/                       # Manifiestos de despliegue para Kubernetes
│   ├── apis.yaml              # Deployments & Services para API Riesgo y API Datos
│   ├── db.yaml                # Deployment & Service para PostgreSQL
│   └── frontend.yaml          # Deployment & Service (LoadBalancer) para el Frontend
├── frontend/                  # Aplicación de React + Vite
│   ├── src/
│   │   ├── components/
│   │   │   ├── DashboardPredictor.jsx  # Formulario y panel de predicción
│   │   │   └── MapaInteractivo.jsx     # Mapa interactivo Leaflet
│   │   ├── App.jsx            # Orquestador visual principal
│   │   └── main.jsx
│   ├── Dockerfile             # Multi-stage build (Node + Nginx)
│   ├── nginx.conf             # Configuración de proxy para producción
│   └── package.json
├── models/                    # Modelos de ML serializados (.pkl)
├── src/                       # Código fuente de las APIs en Python
├── docker-compose.yml         # Orquestación de desarrollo / producción local
├── Dockerfile.api             # Imagen base para las APIs en FastAPI
├── requirements.txt           # Dependencias de Python
├── train_model.py             # Script de entrenamiento del modelo de IA
└── README.md                  # Documentación del proyecto
Guía de Ejecución Local
Pre requisitos
Docker Desktop instalado y ejecutándose.

Git.

1. Clonar el Repositorio
Bash
git clone [https://github.com/TU_USUARIO/incendios-ia.git](https://github.com/TU_USUARIO/incendios-ia.git)
cd incendios-ia
2. Despliegue con Docker Compose (Recomendado)
Para levantar todo el stack tecnológico en contenedores aislados:

Bash
docker compose up --build -d
Una vez completada la construcción, abre tu navegador e ingresa a:
👉 http://localhost

3. Verificar el Estado de los Contenedores
Bash
docker compose ps
☸️ Despliegue en Kubernetes (K8s)
El proyecto cuenta con manifiestos listos para entornos K8s local (Minikube / Docker Desktop K8s) o clústeres en la nube (GKE, EKS, AKS).

Para aplicar las configuraciones en un clúster activo:

Bash
kubectl apply -f k8s/
Para verificar los pods y servicios desplegados:

Bash
kubectl get pods
kubectl get services
🔄 Pipeline de Integración Continua (CI/CD)
El flujo de trabajo configurado en .github/workflows/ci.yml ejecuta las siguientes acciones automáticas ante cada push o pull_request a las ramas main o master:

Checkout automático del código fuente.

Configuración del motor Docker Buildx.

Construcción de imágenes Docker multi-contenedor (docker compose build).

Verificación de inicio y salud de los servicios (docker compose up -d).

🔬 Uso de la Aplicación
Selección de Zona: Haz clic en cualquier punto del mapa interactivo para capturar las coordenadas de la zona a evaluar.

Ingreso de Variables Climáticas: Ajusta la temperatura, humedad, velocidad del viento, porcentaje de vegetación seca e incendios históricos en el panel lateral.

Cálculo de Riesgo: Presiona el botón "Calcular Riesgo".

Resultado: La interfaz mostrará la clasificación de riesgo (BAJO, MEDIO o ALTO) junto con las probabilidades generadas por la red/modelo de IA.
