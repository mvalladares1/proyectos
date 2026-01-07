# 📝 Ejemplo Real de Deploy

**Escenario**: Acabas de agregar un nuevo gráfico en el dashboard de Recepciones

---

## 🔧 Paso 1: Desarrollo Local

```powershell
# En tu máquina Windows
cd 'c:\new\RIO FUTURO\DASHBOARD\proyectos'

# Editar el archivo
code pages/1_Recepciones.py

# Agregar nuevo código (ejemplo):
# - Nueva función para calcular promedio semanal
# - Nuevo gráfico con plotly

# Guardar cambios
```

**Verificar localmente (opcional)**:
```powershell
# Si quieres probar localmente primero
streamlit run Home.py
# Abrir http://localhost:8501 y verificar
```

---

## 📤 Paso 2: Commit y Push

```powershell
# Ver qué cambió
git status

# Agregar cambios
git add pages/1_Recepciones.py

# Commit con mensaje descriptivo
git commit -m "Feature: Agregar gráfico de promedio semanal en Recepciones"

# Subir a GitHub
git push origin main
```

**Resultado**: Código en GitHub, listo para deploy

---

## 🧪 Paso 3: Deploy a DEV (Probar)

```powershell
# Desde tu máquina Windows
ssh debian@167.114.114.51 "cd /home/debian/rio-futuro-dashboards/app && git pull && docker-compose -f docker-compose.dev.yml up -d --build"
```

**Qué pasa en el servidor**:
```bash
# 1. git pull
# Actualiza el código desde GitHub

# 2. docker-compose -f docker-compose.dev.yml up -d --build
# - Reconstruye imagen Docker con el código nuevo
# - Para container DEV viejo
# - Inicia container DEV nuevo con tu cambio
# - Puertos: 8002 (API), 8502 (Web)
```

**Tiempo**: ~2-3 minutos

**Resultado**:
```
Container rio-api-dev  Recreated
Container rio-web-dev  Recreated
Container rio-api-dev  Started
Container rio-api-dev  Healthy
Container rio-web-dev  Started
```

---

## ✅ Paso 4: Verificar en DEV

```
# Abrir en navegador
https://riofuturoprocesos.com/dashboards-dev/
```

**Checklist**:
- [ ] Login funciona
- [ ] Dashboard carga sin errores
- [ ] Tu nuevo gráfico aparece
- [ ] Datos se ven correctos
- [ ] No hay errores en consola del navegador (F12)

**Si hay problemas**:
```bash
# Ver logs
ssh debian@167.114.114.51
docker logs rio-web-dev --tail 50 -f

# Ver errores específicos
docker logs rio-web-dev 2>&1 | grep -i error
```

**Ejemplo de error común**:
```
ModuleNotFoundError: No module named 'pandas'
```
**Solución**: Agregar módulo a `requirements.txt` y rebuild

---

## 🚀 Paso 5: Deploy a PROD (Publicar)

**Solo después de verificar en DEV** ✅

```powershell
# Mismo comando, pero cambia docker-compose.dev.yml → docker-compose.prod.yml
ssh debian@167.114.114.51 "cd /home/debian/rio-futuro-dashboards/app && git pull && docker-compose -f docker-compose.prod.yml up -d --build"
```

**⚠️ Importante**:
- `git pull` trae el **mismo código** que ya probaste en DEV
- **No hay nuevos cambios** entre DEV y PROD
- Solo cambian los puertos (8000, 8501)

**Resultado**:
```
Container rio-api-prod  Recreated
Container rio-web-prod  Recreated
Container rio-api-prod  Started
Container rio-api-prod  Healthy
Container rio-web-prod  Started
```

---

## ✅ Paso 6: Verificar en PROD

```
# Abrir en navegador
https://riofuturoprocesos.com/dashboards/
```

**Checklist**:
- [ ] Login funciona
- [ ] Tu cambio está visible
- [ ] Usuarios pueden acceder normalmente
- [ ] Sin errores en logs

```bash
# Ver logs PROD
ssh debian@167.114.114.51
docker logs rio-web-prod --tail 50

# Ver estado
docker ps --format 'table {{.Names}}\t{{.Status}}'
```

**Éxito**:
```
NAMES          STATUS
rio-web-prod   Up 2 minutes
rio-api-prod   Up 2 minutes (healthy)
rio-web-dev    Up 15 minutes
rio-api-dev    Up 15 minutes (healthy)
```

---

## 🔄 Ejemplo Completo en Una Sesión

```powershell
# 1. DESARROLLO
cd 'c:\new\RIO FUTURO\DASHBOARD\proyectos'
code pages/1_Recepciones.py
# ... hacer cambios ...

# 2. COMMIT
git add pages/1_Recepciones.py
git commit -m "Feature: Agregar gráfico de promedio semanal"
git push origin main

# 3. DEPLOY A DEV
ssh debian@167.114.114.51 "cd /home/debian/rio-futuro-dashboards/app && git pull && docker-compose -f docker-compose.dev.yml up -d --build"

# 4. PROBAR DEV
# Abrir: https://riofuturoprocesos.com/dashboards-dev/
# Verificar que funciona ✓

# 5. DEPLOY A PROD
ssh debian@167.114.114.51 "cd /home/debian/rio-futuro-dashboards/app && git pull && docker-compose -f docker-compose.prod.yml up -d --build"

# 6. VERIFICAR PROD
# Abrir: https://riofuturoprocesos.com/dashboards/
# Confirmar que funciona ✓
```

**Tiempo total**: ~10 minutos (desarrollo) + 5 minutos (deploy y verificación)

---

## 🐛 Qué Hacer Si Algo Falla

### Escenario 1: Error en DEV

```powershell
# Ver qué pasó
ssh debian@167.114.114.51
docker logs rio-web-dev --tail 100

# Si es error de código, arreglarlo
# En tu máquina:
code pages/1_Recepciones.py
# ... fix ...
git add .
git commit -m "Fix: corregir error en gráfico"
git push origin main

# Re-deploy DEV
ssh debian@167.114.114.51 "cd /home/debian/rio-futuro-dashboards/app && git pull && docker-compose -f docker-compose.dev.yml up -d --build"
```

### Escenario 2: Error en PROD

```bash
# Rollback rápido
ssh debian@167.114.114.51
cd /home/debian/rio-futuro-dashboards/app

# Ver commits
git log --oneline -5

# Ejemplo:
# abc1234 (HEAD) Feature: Agregar gráfico promedio ← Este falló
# def5678 Fix: corregir cálculo rendimiento    ← Volver aquí
# ghi9012 Feature: nuevo dashboard compras

# Volver al anterior
git reset --hard def5678

# Rebuild PROD
docker-compose -f docker-compose.prod.yml up -d --build

# PROD ahora tiene el código anterior que funcionaba
```

### Escenario 3: Solo DEV Roto, PROD OK

```bash
# DEV roto NO afecta PROD
# PROD sigue funcionando normal
# Arreglar DEV sin prisa

# Re-sync DEV con PROD actual
ssh debian@167.114.114.51
cd /home/debian/rio-futuro-dashboards/app

# Asegurar mismo código
git fetch
git reset --hard origin/main

# Rebuild DEV
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up -d --build
```

---

## 📊 Resumen Visual

```
┌─────────────────────────────────────────────────────────┐
│ TU MÁQUINA (Windows)                                    │
│                                                         │
│  1. Editar código                                       │
│  2. git push origin main                                │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ GITHUB                                                  │
│  main branch (código único)                             │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ SERVIDOR (167.114.114.51)                               │
│                                                         │
│  git pull ← descarga código                             │
│                                                         │
│  ┌──────────────────┐       ┌──────────────────┐      │
│  │ DEV              │       │ PROD             │      │
│  │ docker-compose   │       │ docker-compose   │      │
│  │ .dev.yml         │       │ .prod.yml        │      │
│  │                  │       │                  │      │
│  │ Puertos:         │       │ Puertos:         │      │
│  │ - API: 8002      │       │ - API: 8000      │      │
│  │ - Web: 8502      │       │ - Web: 8501      │      │
│  │                  │       │                  │      │
│  │ URL:             │       │ URL:             │      │
│  │ /dashboards-dev/ │       │ /dashboards/     │      │
│  └──────────────────┘       └──────────────────┘      │
│                                                         │
│  MISMO CÓDIGO, DIFERENTES CONTAINERS                    │
└─────────────────────────────────────────────────────────┘
```

---

## ✨ Tips

1. **Siempre probar en DEV primero**
   - DEV es tu red de seguridad
   - Errores en DEV no afectan usuarios

2. **git pull automático**
   - Los comandos ya incluyen `git pull`
   - No necesitas hacer `git pull` manual

3. **--build es importante**
   - Fuerza reconstruir imagen con código nuevo
   - Sin `--build` usa imagen vieja en cache

4. **Downtime en PROD**
   - ~30-60 segundos mientras rebuilds
   - Usuarios se desconectan temporalmente
   - Planear en horarios de bajo tráfico

5. **DEV siempre disponible**
   - Puedes romper DEV sin problemas
   - PROD sigue funcionando
   - DEV es para experimentar
