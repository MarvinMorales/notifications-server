import { useState, useCallback, ChangeEvent, FormEvent, useEffect } from 'react';
import "./App.css";

function App() {
  const [user, setUser] = useState<string>("");
  const [id, setId] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const backendURL = "https://agilevirtualassistants.com/api";  // URL del backend Flask
  const publicVapidKey = "BN3MHTt-j8nKyuBXN0oZ-33vNprwK_ukhornL4PNTfTHgPDMV8BYvyW3v-Xo6ttzQxIfjNOcwr1DPvQzcYLU_yA";  // Reemplazar con tu clave pública VAPID

  useEffect(() => {
    const url = window.location.href; 
    const params = new URL(url).searchParams; 
    const survey_id = params.get('survey_id');
    setId(survey_id);
  }, [setId]);

  useEffect(() => {
    if (navigator.serviceWorker.controller) 
      console.log("Service Worker activo.");
    else console.log("No hay Service Worker activo.");
  }, []);

  const urlBase64ToUint8Array = useCallback((base64String: string) => {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/-/g, '+')
      .replace(/_/g, '/');
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    } return outputArray;
  }, []);

  const registerServiceWorker = useCallback(async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await navigator.serviceWorker.register("/serviceWorker.js", {
      scope: "/"
    });

    const register = await navigator.serviceWorker.ready;
    const subscription = await register.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(publicVapidKey)
    });

    setLoading(true);
    await fetch(`${backendURL}/subscription`, {
      method: "POST",
      body: JSON.stringify({ user, subscription }),
      headers: { "Content-Type": "application/json" }
    });

    setTimeout(() => setLoading(false), 3000)
  }, [urlBase64ToUint8Array, setLoading, user]);

  const handleText = (event: ChangeEvent<HTMLInputElement>) => {
    setUser(event.target.value)
  }

  return (
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center" }}>
      <form 
        onSubmit={registerServiceWorker} 
        style={{ display: "flex", flexDirection: "column", alignItems: "flex-start" }}
      >
        { id && ( <h1 style={{ fontSize: 18 }}>Survey ID: {id}</h1> ) }
        <label>Write your name to subscribe notifications</label>
        <div style={{ display: "flex", marginTop: 10 }}>
          <input 
            autoFocus 
            type='text'
            onChange={handleText} 
            placeholder='Example: Manuel' 
            className='input-placeholder'
            style={{ width: 200, height: 44, border: "none", outline: "none", backgroundColor: "white", color: "black", borderRadius: 4, padding: "0 20px", fontSize: 18, marginRight: 10 }} 
          />
          <button 
            type='submit'
            disabled={!user}
            style={{ width: 180, height: 44, borderColor: "#a47e00", borderWidth: 1, borderRadius: 4, cursor: "pointer", color: !user ? "#936e00" : "white", backgroundColor: "#febe05", display: "flex", justifyContent: "center", alignItems: "center" }}
          >
            { !loading ? "Suscribirse" : "Loading..."}
          </button>
        </div>
      </form>
    </div>
  );
}

export default App;
