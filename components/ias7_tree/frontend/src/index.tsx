import React from 'react';
import ReactDOM from 'react-dom/client';
import { Streamlit, withStreamlitConnection, ComponentProps } from 'streamlit-component-lib';
import IAS7Tree from './IAS7Tree';
import { IAS7TreeProps } from './types/ias7';

/**
 * Wrapper component that connects to Streamlit
 */
const IAS7TreeWrapper: React.FC<ComponentProps> = (props) => {
    const { args } = props;

    // Extract props from Streamlit args
    const treeProps: IAS7TreeProps = {
        actividades: args.actividades || [],
        modo: args.modo || 'consolidado',
        efectivo_inicial: args.efectivo_inicial || 0,
        efectivo_final: args.efectivo_final || 0,
        variacion_neta: args.variacion_neta || 0,
        cuentas_sin_clasificar: args.cuentas_sin_clasificar || 0,
        theme: args.theme || 'dark',
    };

    // Set frame height after render
    React.useEffect(() => {
        Streamlit.setFrameHeight();
    });

    return <IAS7Tree {...treeProps} />;
};

// Connect to Streamlit
const ConnectedComponent = withStreamlitConnection(IAS7TreeWrapper);

// Render
const root = ReactDOM.createRoot(
    document.getElementById('root') as HTMLElement
);

root.render(
    <React.StrictMode>
        <ConnectedComponent />
    </React.StrictMode>
);
