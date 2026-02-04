import React, { useEffect, useRef, useState } from "react"
import {
  Streamlit,
  withStreamlitConnection,
} from "streamlit-component-lib"
import Graph from "graphology"
import Sigma from "sigma"
import forceAtlas2 from "graphology-layout-forceatlas2"

const SigmaGraph = (props) => {
  const { nodes, edges, layout, height } = props.args
  const containerRef = useRef(null)
  const sigmaRef = useRef(null)
  const graphRef = useRef(null)
  const [isFullscreen, setIsFullscreen] = useState(false)

  useEffect(() => {
    if (!containerRef.current || !nodes || !edges) return

    // Crear grafo
    const graph = new Graph()
    graphRef.current = graph

    // Agregar nodos
    nodes.forEach((node) => {
      const hasPos = typeof node.x === "number" && typeof node.y === "number"
      graph.addNode(node.id, {
        label: node.label,
        size: node.size || 10,
        color: node.color || "#5B8FF9",
        x: hasPos ? node.x : Math.random(),
        y: hasPos ? node.y : Math.random(),
        detail: node.detail || "",
        originalColor: node.color || "#5B8FF9",
      })
    })

    // Agregar edges
    edges.forEach((edge) => {
      try {
        graph.addEdge(edge.source, edge.target, {
          label: edge.label || "",
          size: edge.size || 2,
          color: edge.color || "#cccccc",
          originalColor: edge.color || "#cccccc",
        })
      } catch (e) {
        console.warn("Edge no agregado:", edge, e)
      }
    })

    // Aplicar layout
    if (layout === "forceatlas2") {
      forceAtlas2.assign(graph, {
        iterations: 100,
        settings: {
          gravity: 1,
          scalingRatio: 10,
          slowDown: 2,
        },
      })
    }

    // Crear renderer
    const sigma = new Sigma(graph, containerRef.current, {
      renderEdgeLabels: false,
      defaultNodeColor: "#5B8FF9",
      defaultEdgeColor: "#cccccc",
      labelSize: 14,
      labelWeight: "bold",
      enableEdgeEvents: true,
    })

    sigmaRef.current = sigma

    // Hover en nodos - opacidad
    sigma.on("enterNode", ({ node }) => {
      
      // Obtener vecinos del nodo
      const neighbors = new Set(graph.neighbors(node))
      neighbors.add(node)

      // Opacidad para nodos no relacionados
      graph.forEachNode((n, attrs) => {
        if (!neighbors.has(n)) {
          graph.setNodeAttribute(n, "color", attrs.originalColor + "33") // 20% opacidad
        }
      })

      // Opacidad para edges no relacionados
      graph.forEachEdge((e, attrs, source, target) => {
        if (!neighbors.has(source) || !neighbors.has(target)) {
          graph.setEdgeAttribute(e, "color", attrs.originalColor + "33")
        }
      })

      sigma.refresh()
    })

    sigma.on("leaveNode", () => {

      // Restaurar colores originales
      graph.forEachNode((n, attrs) => {
        graph.setNodeAttribute(n, "color", attrs.originalColor)
      })

      graph.forEachEdge((e, attrs) => {
        graph.setEdgeAttribute(e, "color", attrs.originalColor)
      })

      sigma.refresh()
    })

    // Click en nodos
    sigma.on("clickNode", ({ node }) => {
      const nodeData = graph.getNodeAttributes(node)
      Streamlit.setComponentValue({
        type: "node_click",
        node: {
          id: node,
          label: nodeData.label,
          detail: nodeData.detail,
        },
      })
    })

    // Click en edges
    sigma.on("clickEdge", ({ edge }) => {
      const edgeData = graph.getEdgeAttributes(edge)
      Streamlit.setComponentValue({
        type: "edge_click",
        edge: {
          id: edge,
          label: edgeData.label,
        },
      })
    })

    // Drag de nodos
    let draggedNode = null
    let isDragging = false

    sigma.on("downNode", (e) => {
      isDragging = true
      draggedNode = e.node
      graph.setNodeAttribute(draggedNode, "highlighted", true)
    })

    sigma.getMouseCaptor().on("mousemovebody", (e) => {
      if (!isDragging || !draggedNode) return

      // Obtener posición del mouse en coordenadas del grafo
      const pos = sigma.viewportToGraph(e)

      // Actualizar posición del nodo
      graph.setNodeAttribute(draggedNode, "x", pos.x)
      graph.setNodeAttribute(draggedNode, "y", pos.y)

      // Prevenir el default pan
      e.preventSigmaDefault()
      e.original.preventDefault()
      e.original.stopPropagation()
    })

    sigma.getMouseCaptor().on("mouseup", () => {
      if (draggedNode) {
        graph.removeNodeAttribute(draggedNode, "highlighted")
      }
      isDragging = false
      draggedNode = null
    })

    sigma.getMouseCaptor().on("mousedown", () => {
      if (!sigma.getCustomBBox()) sigma.setCustomBBox(sigma.getBBox())
    })

    // Notificar que el componente está listo
    Streamlit.setFrameHeight(isFullscreen ? window.innerHeight : height)

    return () => {
      sigma.kill()
    }
  }, [nodes, edges, layout, height, isFullscreen])

  const handleZoomIn = () => {
    if (sigmaRef.current) {
      const camera = sigmaRef.current.getCamera()
      camera.animatedZoom({ duration: 300 })
    }
  }

  const handleZoomOut = () => {
    if (sigmaRef.current) {
      const camera = sigmaRef.current.getCamera()
      camera.animatedUnzoom({ duration: 300 })
    }
  }

  const handleResetView = () => {
    if (sigmaRef.current) {
      const camera = sigmaRef.current.getCamera()
      camera.animatedReset({ duration: 300 })
    }
  }

  const handleFullscreen = () => {
    if (!document.fullscreenElement) {
      containerRef.current?.parentElement?.requestFullscreen()
      setIsFullscreen(true)
    } else {
      document.exitFullscreen()
      setIsFullscreen(false)
    }
  }

  return (
    <div style={{ position: "relative", width: "100%", height: `${height}px` }}>
      {/* Controles */}
      <div
        style={{
          position: "absolute",
          top: "10px",
          right: "10px",
          zIndex: 1000,
          display: "flex",
          flexDirection: "column",
          gap: "5px",
        }}
      >
        <button
          onClick={handleZoomIn}
          style={{
            width: "40px",
            height: "40px",
            border: "1px solid #ddd",
            borderRadius: "4px",
            background: "white",
            cursor: "pointer",
            fontSize: "20px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
          title="Zoom In"
        >
          +
        </button>
        <button
          onClick={handleZoomOut}
          style={{
            width: "40px",
            height: "40px",
            border: "1px solid #ddd",
            borderRadius: "4px",
            background: "white",
            cursor: "pointer",
            fontSize: "20px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
          title="Zoom Out"
        >
          −
        </button>
        <button
          onClick={handleResetView}
          style={{
            width: "40px",
            height: "40px",
            border: "1px solid #ddd",
            borderRadius: "4px",
            background: "white",
            cursor: "pointer",
            fontSize: "16px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
          title="Reset View"
        >
          ⟲
        </button>
        <button
          onClick={handleFullscreen}
          style={{
            width: "40px",
            height: "40px",
            border: "1px solid #ddd",
            borderRadius: "4px",
            background: "white",
            cursor: "pointer",
            fontSize: "16px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
          title="Fullscreen"
        >
          ⛶
        </button>
      </div>

      {/* Contenedor del grafo */}
      <div
        ref={containerRef}
        style={{
          width: "100%",
          height: "100%",
          border: "1px solid #ddd",
          borderRadius: "4px",
          background: "#fafafa",
        }}
      />
    </div>
  )
}

export default withStreamlitConnection(SigmaGraph)
