import React from 'react';
import { IAS7Account } from '../types/ias7';
import { formatMonto, formatPct, getMontoColor } from '../utils/formatters';

interface CompositionTableProps {
    cuentas: IAS7Account[];
    subtotal: number;
    conceptoId: string;
}

const CompositionTable: React.FC<CompositionTableProps> = ({ cuentas, subtotal, conceptoId }) => {
    const divisor = Math.abs(subtotal) || 1;

    return (
        <div className="ias7-composition">
            <div className="ias7-drilldown__title">📊 Composición contable ({conceptoId})</div>

            <div className="ias7-table">
                <div className="ias7-table__header">
                    <span className="ias7-table__col ias7-table__col--codigo">Código</span>
                    <span className="ias7-table__col ias7-table__col--nombre">Nombre</span>
                    <span className="ias7-table__col ias7-table__col--monto">Monto</span>
                    <span className="ias7-table__col ias7-table__col--pct">% Línea</span>
                </div>

                {cuentas.slice(0, 15).map((cuenta, idx) => {
                    const pct = (Math.abs(cuenta.monto) / divisor) * 100;
                    const color = getMontoColor(cuenta.monto);
                    const montoDisplay = cuenta.monto >= 0
                        ? `+$${Math.abs(cuenta.monto).toLocaleString('es-CL', { maximumFractionDigits: 0 })}`
                        : `-$${Math.abs(cuenta.monto).toLocaleString('es-CL', { maximumFractionDigits: 0 })}`;

                    return (
                        <div key={cuenta.codigo || idx} className="ias7-table__row">
                            <span className="ias7-table__col ias7-table__col--codigo">{cuenta.codigo}</span>
                            <span className="ias7-table__col ias7-table__col--nombre" title={cuenta.nombre}>
                                {cuenta.nombre.substring(0, 40)}
                            </span>
                            <span className="ias7-table__col ias7-table__col--monto" style={{ color }}>
                                {montoDisplay}
                            </span>
                            <span className="ias7-table__col ias7-table__col--pct">{formatPct(pct)}</span>
                        </div>
                    );
                })}
            </div>

            {cuentas.length > 15 && (
                <div style={{ color: '#718096', fontSize: '0.85em', marginTop: '8px' }}>
                    ... y {cuentas.length - 15} cuentas más
                </div>
            )}
        </div>
    );
};

export default CompositionTable;
