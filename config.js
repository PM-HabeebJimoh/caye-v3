// CAYE v3.0 — Dynamic URL Configuration

const getApiUrl = () => {
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL;
  }
  return 'http://localhost:8000';
};

const getWsUrl = () => {
  if (process.env.REACT_APP_WS_URL) {
    return process.env.REACT_APP_WS_URL;
  }
  return 'ws://localhost:8000/ws';
};

export const API_URL = getApiUrl();
export const WS_URL = getWsUrl();
