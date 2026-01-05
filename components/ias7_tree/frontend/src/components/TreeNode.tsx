import React, { useState } from 'react';
import { Streamlit } from "streamlit-component-lib";
import { IAS7Node, ViewMode } from '../types/ias7';
import { getIndent, formatMonto, formatPct, getMontoColor } from '../utils/formatters';
import MontoDisplay from './MontoDisplay';
import CompositionTable from './CompositionTable';

interface TreeNodeProps {
    node: IAS7Node;
    modo: ViewMode;
    activityColor: string;
}

const TreeNode: React.FC<TreeNodeProps> = ({ node, modo, activityColor }) => {
    const [expanded, setExpanded] = useState(false);

    React.useEffect(() => {
        if (expanded) {
            // Multiple attempts to ensure height catches up
            setTimeout(() => Streamlit.setFrameHeight(), 100);
            setTimeout(() => Streamlit.setFrameHeight(), 300);
        }
    }, [expanded]);

    const { id, nombre, tipo, nivel, monto_real, monto_proyectado, cuentas, documentos } = node;

    // Calculate display amount based on mode
    const monto = modo === 'real' ? monto_real :
        modo === 'proyectado' ? monto_proyectado :
            monto_real + monto_proyectado;

    const indent = getIndent(nivel);
    const hasDrilldown = (cuentas && cuentas.length > 0) || (documentos && documentos.length > 0);
    const isClickable = tipo === 'LINEA' && hasDrilldown;
    const isHeader = tipo === 'HEADER';
    const isTotal = tipo === 'TOTAL';

    // Base classes
    let nodeClass = 'ias7-grid-row';
    if (isHeader) nodeClass += ' ias7-node--header';
    if (isTotal) nodeClass += ' ias7-node--total';
    if (tipo === 'LINEA') nodeClass += ' ias7-node--linea';

    // Styles for borders/colors
    const rowStyle: React.CSSProperties = {};
    if (isHeader && nivel === 1) {
        rowStyle.borderLeft = `4px solid ${activityColor}`;
    }
    if (isTotal) {
        rowStyle.color = activityColor;
    }

    // Icons (Master Spec)
    // Activity handles its own icon in ActivitySection. Here we handle Header/Total/Line
    let icon = '';
    if (isHeader) icon = '📁';
    else if (isTotal) icon = 'Σ';
    // else if (tipo === 'LINEA') icon = '▸';  <-- Removed to prevent double arrows

    // Dual Mode Logic
    const isConsolidado = modo === 'consolidado';
    if (isConsolidado) nodeClass += ' ias7-grid-row--dual';

    return (
        <>
            <div
                className={nodeClass}
                style={rowStyle}
                onClick={() => isClickable && setExpanded(!expanded)}
                role={isClickable ? 'button' : undefined}
            >
                {/* COL 1: Indent & Expand Marker */}
                <div className="ias7-node__indent-marker" style={{ paddingLeft: `${indent}px` }}>
                    {isClickable && (
                        <span className={`ias7-expand-icon ${expanded ? 'ias7-expand-icon--expanded' : ''}`}>
                            ▶
                        </span>
                    )}
                </div>

                {/* COL 2: ID Code (Hidden per UX Master Spec, moved to tooltip) */}
                {/* Removed visible div, ID is used in key/logic but not shown */}

                {/* COL 3: Name */}
                <div className="ias7-node__nombre" title={`${id} - ${nombre}`}>
                    {/* Fixed width container for alignment */}
                    <span style={{
                        display: 'inline-flex',
                        justifyContent: 'center',
                        width: '24px',
                        marginRight: '8px',
                        opacity: 0.7
                    }}>
                        {icon}
                    </span>
                    {nombre}
                </div>

                {/* COL 4 (Real in Dual) or Main Amount */}
                <div className="ias7-node__monto">
                    {/* Header for column if it's the Total line or Header? */}
                    {isConsolidado && isHeader && <span className="ias7-monto-label">Real</span>}

                    {(isTotal || (tipo === 'LINEA')) && (
                        isConsolidado ? (
                            <MontoDisplay valor={monto_real} showZero={isTotal} />
                        ) : (
                            // Single Mode (Sum or Specific) - WITH PARETO TOOLTIP
                            <div className="ias7-tooltip-wrapper">
                                <MontoDisplay valor={monto} showZero={isTotal} />
                                {tipo === 'LINEA' && cuentas && cuentas.length > 0 && (
                                    <div className="ias7-tooltip-content">
                                        <div className="ias7-tooltip-header">Top Contribuyentes</div>
                                        {cuentas
                                            .sort((a, b) => Math.abs(b.monto) - Math.abs(a.monto))
                                            .slice(0, 3)
                                            .map((cta, idx) => (
                                                <div key={idx} className="ias7-tooltip-item">
                                                    <div className="ias7-tooltip-name">{cta.nombre.substring(0, 25)}...</div>
                                                    <div className="ias7-tooltip-val">{formatMonto(cta.monto)}</div>
                                                </div>
                                            ))
                                        }
                                        {cuentas.length > 3 && (
                                            <div className="ias7-tooltip-more">... y {cuentas.length - 3} más</div>
                                        )}
                                    </div>
                                )}
                            </div>
                        )
                    )}
                </div>

                {/* COL 5: Projected (Only in Dual) */}
                {isConsolidado && (
                    <div className="ias7-node__monto">
                        {isHeader && <span className="ias7-monto-label">Proyectado</span>}
                        {(isTotal || tipo === 'LINEA') && (
                            <MontoDisplay valor={monto_proyectado} showZero={isTotal} />
                        )}
                    </div>
                )}

                {/* COL 6: Actions (Edit) */}
                <div className="ias7-node__actions">
                    {tipo === 'LINEA' && (
                        <button
                            className="ias7-action-btn"
                            onClick={(e) => {
                                e.stopPropagation();
                                Streamlit.setComponentValue({
                                    action: "EDIT_NODE",
                                    payload: { id, nombre, monto_real }
                                });
                            }}
                            title="Editar Mapeo"
                        >
                            ✏️
                        </button>
                    )}
                </div>
            </div>

            {/* Drilldown Content (Full Width or indented) */}
            {expanded && hasDrilldown && (
                <div className="ias7-drilldown" style={{ marginLeft: '40px', gridColumn: '1 / -1' }}>
                    {cuentas && cuentas.length > 0 && (
                        <CompositionTable cuentas={cuentas} subtotal={monto} conceptoId={id} />
                    )}
                    {documentos && documentos.length > 0 && (
                        <div className="ias7-drilldown__docs">
                            <div className="ias7-drilldown__title">🟡 Documentos Proyectados ({id})</div>
                            {/* DocumentsTable would go here */}
                        </div>
                    )}
                </div>
            )}
        </>
    );
};

export default TreeNode;