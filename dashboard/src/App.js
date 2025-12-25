import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [token, setToken] = useState(null);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [stats, setStats] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Check if already logged in
    const savedToken = localStorage.getItem('apds_token');
    if (savedToken) {
      setToken(savedToken);
      setLoggedIn(true);
      fetchData(savedToken);
    }
  }, []);

  useEffect(() => {
    if (loggedIn && token) {
      const interval = setInterval(() => {
        fetchData(token);
      }, 5000); // Refresh every 5 seconds
      return () => clearInterval(interval);
    }
  }, [loggedIn, token]);

  const login = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post(`${API_URL}/auth/login`, {
        username,
        password
      });
      const newToken = response.data.access_token;
      setToken(newToken);
      setLoggedIn(true);
      localStorage.setItem('apds_token', newToken);
      fetchData(newToken);
      setError(null);
    } catch (err) {
      setError('Login failed. Use: admin/admin123, operator/operator123, or viewer/viewer123');
    }
  };

  const logout = () => {
    setToken(null);
    setLoggedIn(false);
    localStorage.removeItem('apds_token');
    setStats(null);
    setAlerts([]);
  };

  const fetchData = async (authToken) => {
    try {
      const headers = { Authorization: `Bearer ${authToken}` };
      
      // Fetch stats
      const [cvStats, mlStats, alertStats, alertsData] = await Promise.all([
        axios.get(`${API_URL}/cv/stats`, { headers }).catch(() => null),
        axios.get(`${API_URL}/ml/stats`, { headers }).catch(() => null),
        axios.get(`${API_URL}/alerts/stats`, { headers }).catch(() => null),
        axios.get(`${API_URL}/alerts/recent?limit=10`, { headers }).catch(() => null)
      ]);

      setStats({
        cv: cvStats?.data,
        ml: mlStats?.data,
        alerts: alertStats?.data
      });

      if (alertsData?.data) {
        setAlerts(alertsData.data);
      }
    } catch (err) {
      console.error('Failed to fetch data:', err);
    }
  };

  const acknowledgeAlert = async (alertId) => {
    try {
      await axios.post(
        `${API_URL}/alerts/${alertId}/acknowledge?username=${username}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      fetchData(token);
    } catch (err) {
      setError('Failed to acknowledge alert');
    }
  };

  if (!loggedIn) {
    return (
      <div className="login-container">
        <div className="login-box">
          <h1>APDS Dashboard</h1>
          <h2>Autonomous Perimeter Defense System</h2>
          <form onSubmit={login}>
            <input
              type="text"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <button type="submit">Login</button>
          </form>
          {error && <div className="error">{error}</div>}
          <div className="login-hint">
            <p>Demo Credentials:</p>
            <p>admin / admin123</p>
            <p>operator / operator123</p>
            <p>viewer / viewer123</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>APDS - Autonomous Perimeter Defense System</h1>
        <button onClick={logout} className="logout-btn">Logout</button>
      </header>

      <div className="dashboard-content">
        <div className="stats-grid">
          <div className="stat-card">
            <h3>CV Detection Stats</h3>
            {stats?.cv ? (
              <div>
                <p>Total Detections: {stats.cv.total_detections || 0}</p>
                <p>High Confidence: {stats.cv.high_confidence_detections || 0}</p>
                <p>Persons Detected: {stats.cv.person_detections || 0}</p>
                <p>Vehicles Detected: {stats.cv.vehicle_detections || 0}</p>
                <p>Model Status: {stats.cv.model_loaded ? '✓ Loaded' : '✗ Not Loaded'}</p>
              </div>
            ) : (
              <p>Loading...</p>
            )}
          </div>

          <div className="stat-card">
            <h3>ML Classification Stats</h3>
            {stats?.ml ? (
              <div>
                <p>Total Classifications: {stats.ml.total_classifications || 0}</p>
                <p>High Threat: {stats.ml.high_threat_classifications || 0}</p>
                <p>Critical: {stats.ml.critical_threat_classifications || 0}</p>
                <p>Avg Threat Score: {(stats.ml.average_threat_score || 0).toFixed(2)}</p>
                <p>Model Status: {stats.ml.model_loaded ? '✓ Loaded' : '✗ Rule-based'}</p>
              </div>
            ) : (
              <p>Loading...</p>
            )}
          </div>

          <div className="stat-card">
            <h3>Alert Stats</h3>
            {stats?.alerts ? (
              <div>
                <p>Total Alerts: {stats.alerts.total_alerts || 0}</p>
                <p>Critical: {stats.alerts.critical_alerts || 0}</p>
                <p>High Threat: {stats.alerts.high_threat_alerts || 0}</p>
                <p>Acknowledged: {stats.alerts.acknowledged_alerts || 0}</p>
                <p>Active Alerts: {stats.alerts.active_alerts || 0}</p>
              </div>
            ) : (
              <p>Loading...</p>
            )}
          </div>
        </div>

        <div className="alerts-section">
          <h2>Recent Alerts</h2>
          <div className="alerts-list">
            {alerts.length > 0 ? (
              alerts.map((alert) => (
                <div
                  key={alert.alert_id}
                  className={`alert-item ${alert.threat_category}`}
                >
                  <div className="alert-header">
                    <span className="alert-id">{alert.alert_id}</span>
                    <span className={`threat-badge ${alert.threat_category}`}>
                      {alert.threat_category}
                    </span>
                    <span className="threat-score">
                      Score: {(alert.threat_score * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="alert-body">
                    <p>{alert.explanation}</p>
                    <p className="alert-time">
                      {new Date(alert.timestamp).toLocaleString()}
                    </p>
                  </div>
                  {!alert.acknowledged && (
                    <button
                      onClick={() => acknowledgeAlert(alert.alert_id)}
                      className="acknowledge-btn"
                    >
                      Acknowledge
                    </button>
                  )}
                  {alert.acknowledged && (
                    <div className="acknowledged">
                      Acknowledged by {alert.acknowledged_by} at{' '}
                      {new Date(alert.acknowledged_at).toLocaleString()}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <p>No alerts</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;

