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

    // Determine styles based on type
    let nodeClass = 'ias7-node';
    if (tipo === 'HEADER') {
        nodeClass += ` ias7-node--header ias7-node--level-${nivel}`;
    } else if (tipo === 'LINEA') {
        nodeClass += ' ias7-node--linea';
    } else if (tipo === 'TOTAL') {
        nodeClass += ' ias7-node--total';
    }

    // Border left for headers
    const borderStyle = tipo === 'HEADER' || tipo === 'TOTAL'
        ? { borderLeft: `4px solid ${activityColor}` }
        : {};

    // Background for totals
    const bgStyle = tipo === 'TOTAL'
        ? { background: `${activityColor}15` }
        : {};

    // Should show amount?
    const showMonto = tipo === 'TOTAL' || (tipo === 'LINEA' && monto !== 0);

    return (
        <>
            <div
                className={nodeClass}
                style={{ marginLeft: `${indent}px`, ...borderStyle, ...bgStyle }}
                onClick={() => isClickable && setExpanded(!expanded)}
                role={isClickable ? 'button' : undefined}
            >
                <div className="ias7-node__left">
                    {isClickable && (
                        <span className={`ias7-expand-icon ${expanded ? 'ias7-expand-icon--expanded' : ''}`}>
                            ▶
                        </span>
                    )}
                    <span className="ias7-node__id">{id}</span>
                    <span className="ias7-node__nombre">{nombre}</span>
                </div>
                {showMonto && <MontoDisplay valor={monto} showZero={tipo === 'TOTAL'} />}
            </div>

            {expanded && hasDrilldown && (
                <div className="ias7-drilldown" style={{ marginLeft: `${indent + 30}px` }}>
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
