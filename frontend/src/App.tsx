import { useEffect, useState } from "react";
import axios from "axios";

function App() {
  const [backendStatus, setBackendStatus] = useState<
    "loading" | "connected" | "error"
  >("loading");
  const [errorMessage, setErrorMessage] = useState<string>("");

  useEffect(() => {
    const checkBackend = async () => {
      try {
        const response = await axios.get("http://localhost:8000/health");
        if (response.data.status === "ok") {
          setBackendStatus("connected");
        }
      } catch (error) {
        setBackendStatus("error");
        if (axios.isAxiosError(error)) {
          setErrorMessage(
            error.message || "Failed to connect to backend"
          );
        } else {
          setErrorMessage("Failed to connect to backend");
        }
      }
    };

    checkBackend();
  }, []);

  return (
    <div className="container">
      <h1>Network Monitor</h1>

      <div className="status-card">
        {backendStatus === "loading" && (
          <p className="status-loading">Checking backend connection...</p>
        )}
        {backendStatus === "connected" && (
          <p className="status-connected">✓ Backend connected</p>
        )}
        {backendStatus === "error" && (
          <>
            <p className="status-error">✗ Backend connection failed</p>
            <p className="error-message">{errorMessage}</p>
            <p className="hint">
              Make sure the backend is running on http://localhost:8000
            </p>
          </>
        )}
      </div>
    </div>
  );
}

export default App;
