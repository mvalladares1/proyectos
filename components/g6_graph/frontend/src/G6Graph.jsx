import React, { useEffect, useRef } from "react"
import { Streamlit, withStreamlitConnection } from "streamlit-component-lib"
import G6 from "@antv/g6"
import dagre from "dagre"

// Registrar layout dagre personalizado
G6.registerLayout("dagre-custom", {
  getDefaultCfg() {
    return {
      rankdir: "LR",
      align: undefined,
      nodesep: 50,
      ranksep: 100,
      controlPoints: true
    }
  },
  
  execute() {
    const self = this
    const { nodes, edges } = self
    const { rankdir, nodesep, ranksep, align } = self

    const g = new dagre.graphlib.Graph()
    g.setGraph({
      rankdir,
      nodesep,
      ranksep,
      align
    })
    g.setDefaultEdgeLabel(() => ({}))

    // Agregar nodos
    nodes.forEach(node => {
      g.setNode(node.id, {
        width: node.size?.[0] || 150,
        height: node.size?.[1] || 60
      })
    })

    // Agregar edges
    edges.forEach(edge => {
      g.setEdge(edge.source, edge.target)
    })

    // Ejecutar layout
    dagre.layout(g)

    // Aplicar posiciones
    g.nodes().forEach(nodeId => {
      const node = nodes.find(n => n.id === nodeId)
      if (node) {
        const dagreNode = g.node(nodeId)
        node.x = dagreNode.x
        node.y = dagreNode.y
      }
    })

    // Calcular puntos de control para edges curvos
    edges.forEach(edge => {
      const points = g.edge(edge.source, edge.target).points
      if (points && points.length > 2) {
        edge.controlPoints = points.slice(1, -1)
      }
    })
  }
})

function G6Graph(props) {
  const { nodes, edges, layout, direction, height } = props.args
  const containerRef = useRef(null)
  const graphRef = useRef(null)

  useEffect(() => {
    if (!containerRef.current || !nodes || !edges) return

    // Configuración del grafo
    const graph = new G6.Graph({
      container: containerRef.current,
      width: containerRef.current.offsetWidth,
      height: height || 800,
      modes: {
        default: [
          "drag-canvas",
          "zoom-canvas",
          {
            type: "drag-node",
            enableDelegate: true
          }
        ]
      },
      layout: {
        type: "dagre-custom",
        rankdir: direction || "LR",
        nodesep: 80,
        ranksep: 150,
        controlPoints: true
      },
      defaultNode: {
        type: "rect",
        size: [150, 60],
        style: {
          fill: "#5B8FF9",
          stroke: "#2f54eb",
          lineWidth: 2,
          radius: 4
        },
        labelCfg: {
          style: {
            fill: "#fff",
            fontSize: 12,
            fontWeight: "bold"
          }
        }
      },
      defaultEdge: {
        type: "polyline",
        style: {
          stroke: "#b5b5b5",
          lineWidth: 2,
          endArrow: {
            path: G6.Arrow.triangle(10, 12, 0),
            fill: "#b5b5b5"
          }
        },
        labelCfg: {
          autoRotate: true,
          style: {
            fill: "#666",
            fontSize: 10,
            background: {
              fill: "#fff",
              padding: [2, 4, 2, 4],
              radius: 2
            }
          }
        }
      }
    })

    // Procesar nodos
    const processedNodes = nodes.map(node => ({
      id: node.id,
      label: node.label || node.id,
      size: node.size || [150, 60],
      style: {
        fill: node.color || "#5B8FF9",
        stroke: node.borderColor || "#2f54eb",
        lineWidth: node.borderWidth || 2,
        radius: 4
      },
      labelCfg: {
        style: {
          fill: node.labelColor || "#fff",
          fontSize: node.labelSize || 12
        }
      }
    }))

    // Procesar edges con grosor proporcional al value
    const maxValue = Math.max(...edges.map(e => e.value || 1))
    const processedEdges = edges.map(edge => ({
      source: edge.source,
      target: edge.target,
      label: edge.label || (edge.value ? `${edge.value}` : ""),
      style: {
        stroke: edge.color || "#b5b5b5",
        lineWidth: edge.value ? Math.max(2, (edge.value / maxValue) * 15) : 2,
        opacity: edge.opacity || 0.6,
        endArrow: {
          path: G6.Arrow.triangle(10, 12, 0),
          fill: edge.color || "#b5b5b5"
        }
      }
    }))

    // Cargar datos
    graph.data({
      nodes: processedNodes,
      edges: processedEdges
    })

    graph.render()

    // Fit view con padding
    graph.fitView(20)

    // Event listeners
    graph.on("node:click", (evt) => {
      Streamlit.setComponentValue({
        type: "node_click",
        node: evt.item.getModel()
      })
    })

    graph.on("edge:click", (evt) => {
      Streamlit.setComponentValue({
        type: "edge_click",
        edge: evt.item.getModel()
      })
    })

    graphRef.current = graph

    // Cleanup
    return () => {
      if (graphRef.current) {
        graphRef.current.destroy()
      }
    }
  }, [nodes, edges, layout, direction, height])

  // Resize handler
  useEffect(() => {
    const handleResize = () => {
      if (graphRef.current && containerRef.current) {
        graphRef.current.changeSize(
          containerRef.current.offsetWidth,
          height || 800
        )
        graphRef.current.fitView(20)
      }
    }

    window.addEventListener("resize", handleResize)
    Streamlit.setFrameHeight()

    return () => {
      window.removeEventListener("resize", handleResize)
    }
  }, [height])

  return (
    <div style={{ width: "100%", height: height || 800 }}>
      <div ref={containerRef} style={{ width: "100%", height: "100%" }} />
    </div>
  )
}

export default withStreamlitConnection(G6Graph)
