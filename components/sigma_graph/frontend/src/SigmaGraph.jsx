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

  useEffect(() => {
    if (!containerRef.current || !nodes || !edges) return

    // Crear grafo
    const graph = new Graph()

    // Agregar nodos
    nodes.forEach((node) => {
      graph.addNode(node.id, {
        label: node.label,
        size: node.size || 10,
        color: node.color || "#5B8FF9",
        x: Math.random(),
        y: Math.random(),
        detail: node.detail || "",
      })
    })

    // Agregar edges
    edges.forEach((edge) => {
      try {
        graph.addEdge(edge.source, edge.target, {
          label: edge.label || "",
          size: edge.size || 2,
          color: edge.color || "#cccccc",
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
      renderEdgeLabels: true,
      defaultNodeColor: "#5B8FF9",
      defaultEdgeColor: "#cccccc",
      labelSize: 14,
      labelWeight: "bold",
    })

    sigmaRef.current = sigma

    // Eventos de click
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

    // Notificar que el componente está listo
    Streamlit.setFrameHeight(height)

    return () => {
      sigma.kill()
    }
  }, [nodes, edges, layout, height])

  return (
    <div
      ref={containerRef}
      style={{
        width: "100%",
        height: `${height}px`,
        border: "1px solid #ddd",
        borderRadius: "4px",
      }}
    />
  )
}

export default withStreamlitConnection(SigmaGraph)
