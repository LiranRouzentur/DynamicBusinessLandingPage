import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'
import { BuildProvider } from './contexts/BuildContext'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BuildProvider>
      <App />
    </BuildProvider>
  </React.StrictMode>,
)


