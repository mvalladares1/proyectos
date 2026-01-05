import React from 'react';
import { formatMonto, getMontoColor, getIndent } from '../utils/formatters';
import { IAS7Node, ViewMode } from '../types/ias7';

interface MontoDisplayProps {
    valor: number;
    showZero?: boolean;
}

export const MontoDisplay: React.FC<MontoDisplayProps> = ({ valor, showZero = false }) => {
    if (valor === 0 && !showZero) {
        return null;
    }

    const color = getMontoColor(valor);
    const className = valor > 0 ? 'ias7-node__monto--positive' :
        valor < 0 ? 'ias7-node__monto--negative' :
            'ias7-node__monto--zero';

    return (
        <span className={`ias7-node__monto ${className}`} style={{ color }}>
            {formatMonto(valor)}
        </span>
    );
};

export default MontoDisplay;
