import sys

# Leer archivo
with open("/home/debian/proyectos/stock-picking/frontend/src/pages/ScanPallet.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# Fix 1: Mejorar onChange del input de pallet para detectar CAM
old_pallet_onchange = """                        onChange={(e) => {
                            const value = e.target.value.toUpperCase()
                            // Limitar a 11 caracteres (PACK0026966)
                            if (value.length <= 11) {
                                setManualBarcode(value)
                            }
                        }}"""

new_pallet_onchange = """                        onChange={(e) => {
                            const value = e.target.value.toUpperCase()
                            
                            // Si empieza con CAM, moverlo a ubicación
                            if (value.startsWith("CAM")) {
                                searchLocationByBarcode(value)
                                setManualBarcode('')
                                return
                            }
                            
                            // Limitar a 11 caracteres (PACK0026966)
                            if (value.length <= 11) {
                                setManualBarcode(value)
                            }
                        }}"""

content = content.replace(old_pallet_onchange, new_pallet_onchange)

# Fix 2: Mejorar onChange del input de ubicación para detectar PACK
old_location_onchange = """                                onChange={(e) => setLocationBarcode(e.target.value)}"""

new_location_onchange = """                                onChange={(e) => {
                                    const value = e.target.value.toUpperCase()
                                    
                                    // Si empieza con PACK, agregarlo como pallet
                                    if (value.startsWith("PACK")) {
                                        const palletCode = value.substring(0, 11)
                                        addBarcode(palletCode)
                                        setLocationBarcode('')
                                        return
                                    }
                                    
                                    setLocationBarcode(value)
                                }}"""

content = content.replace(old_location_onchange, new_location_onchange)

# Fix 3: Reemplazar botón de cámara por botón de limpiar en ubicación
old_camera_button = """                            <Button
                                onClick={openLocationScanner}
                                className="px-2"
                                variant="secondary"
                            >
                                <FiCamera className="w-4 h-4" />
                            </Button>"""

new_clear_button = """                            {locationBarcode && (
                                <Button
                                    onClick={() => {
                                        setLocationBarcode('')
                                        locationInputRef.current?.focus()
                                    }}
                                    className="px-2"
                                    variant="ghost"
                                    title="Limpiar"
                                >
                                    <FiX className="w-4 h-4" />
                                </Button>
                            )}"""

content = content.replace(old_camera_button, new_clear_button)

# Fix 4: Arreglar el listener global - agregar addBarcode y searchLocationByBarcode a las dependencias
old_deps = """    }, [isScannerOpen, scannedItems, isOnline])"""
new_deps = """    }, [isScannerOpen, addBarcode, searchLocationByBarcode])"""

content = content.replace(old_deps, new_deps)

# Escribir archivo
with open("/home/debian/proyectos/stock-picking/frontend/src/pages/ScanPallet.tsx", "w", encoding="utf-8") as f:
    f.write(content)

print("✓ Cambios aplicados correctamente")
