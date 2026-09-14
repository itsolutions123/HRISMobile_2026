import React, { createContext, useState } from 'react';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const API_BASE_URL = 'http://10.0.10.37:8089';

  const login = async (employeeId, password, department) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ employee_id: employeeId, password }),
      });

      if (!response.ok) {
        throw new Error('Invalid Employee ID or Password');
      }

      const data = await response.json();
      if (data.status === 'success' && data.user) {
        setUser(data.user);
        return true;
      }
      return false;
    } catch (error) {
      console.log('Login Error:', error.message);
      return false;
    }
  };

  const logout = () => {
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, API_BASE_URL }}>
      {children}
    </AuthContext.Provider>
  );
};
