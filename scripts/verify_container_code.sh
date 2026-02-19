#!/bin/bash
# Script para verificar si el código correcto está en el contenedor
# Ejecutar en el servidor: bash scripts/verify_container_code.sh

echo "=========================================="
echo "VERIFICACIÓN DE CÓDIGO EN CONTENEDOR"
echo "=========================================="

# 1. Verificar que el contenedor existe
echo -e "\n1. Contenedores rio activos:"
docker ps --filter "name=rio" --format "table {{.Names}}\t{{.Status}}"

# 2. Verificar el código dentro del contenedor
echo -e "\n2. Buscando 'periodo_proyectado' en el código del contenedor:"
docker exec rio-api-dev grep -n "periodo_proyectado" /app/backend/services/flujo_caja/real_proyectado.py | head -10

# 3. Verificar que x_studio_fecha_estimada_de_pago está en el query
echo -e "\n3. Buscando 'x_studio_fecha_estimada_de_pago' en calcular_cobros_clientes:"
docker exec rio-api-dev grep -n "x_studio_fecha_estimada_de_pago" /app/backend/services/flujo_caja/real_proyectado.py

# 4. Verificar el hash del commit en el servidor local
echo -e "\n4. Commit actual en el servidor (git):"
git log --oneline -1

# 5. Comparar con lo que debería tener
echo -e "\n5. El código correcto debe tener estas líneas en calcular_cobros_clientes:"
echo "   - 'x_studio_fecha_estimada_de_pago' en el search_read"
echo "   - periodo_real vs periodo_proyectado separados"
echo "   - Conversión USD a CLP"

echo -e "\n=========================================="
echo "Si NO aparece 'x_studio_fecha_estimada_de_pago' en paso 3,"
echo "el contenedor tiene código VIEJO."
echo ""
echo "SOLUCIÓN:"
echo "  git pull"
echo "  docker-compose -f docker-compose.dev.yml down"
echo "  docker-compose -f docker-compose.dev.yml build --no-cache"
echo "  docker-compose -f docker-compose.dev.yml up -d"
echo "=========================================="
