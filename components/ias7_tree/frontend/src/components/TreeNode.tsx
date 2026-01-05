import React, { useState } from 'react';
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

    // Icons
    const icon = isHeader ? '📂' : isTotal ? 'Σ' : '📄';

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

                {/* COL 2: ID Code */}
                <div className="ias7-node__id">
                    {id}
                </div>

                {/* COL 3: Name */}
                <div className="ias7-node__nombre" title={nombre}>
                    {isHeader && <span style={{ opacity: 0.5, marginRight: 6 }}>{icon}</span>}
                    {nombre}
                </div>

                {/* COL 4: Amount */}
                <div className="ias7-node__monto">
                    {(isTotal || (tipo === 'LINEA' && monto !== 0)) && (
                        <MontoDisplay valor={monto} showZero={isTotal} />
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
