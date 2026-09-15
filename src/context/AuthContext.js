import React, { createContext, useState } from 'react';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const API_BASE_URL = 'http://10.0.10.37:8089';

  const parseErrorMessage = (detail, fallbackMsg) => {
    if (!detail) return fallbackMsg;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail.map(item => {
        const field = item.loc ? item.loc[item.loc.length - 1] : '';
        return field ? `${field}: ${item.msg}` : (item.msg || JSON.stringify(item));
      }).join('\n');
    }
    if (typeof detail === 'object') {
      return detail.msg || JSON.stringify(detail);
    }
    return String(detail);
  };

  const login = async (employeeId, password, department) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ employee_id: employeeId, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        const errMsg = parseErrorMessage(data.detail, 'Invalid Employee ID or Password');
        return { success: false, message: errMsg };
      }

      if (data.status === 'success' && data.user) {
        setUser(data.user);
        if (data.access_token) {
          setToken(data.access_token);
        }
        return { success: true, message: 'Login successful' };
      }
      return { success: false, message: 'Invalid response from server' };
    } catch (error) {
      console.log('Login Error:', error.message);
      return { success: false, message: error.message };
    }
  };

  const register = async (firstName, lastName, suffix, email, password, department, mobilePhone) => {
    try {
      const payload = {
        first_name: firstName,
        last_name: lastName,
        suffix: suffix && suffix.trim() ? suffix.trim() : null,
        email: email,
        password: password,
        department: department,
        mobile_phone: mobilePhone && mobilePhone.trim() ? mobilePhone.trim() : null,
      };

      const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok) {
        const errMsg = parseErrorMessage(data.detail, 'Registration failed');
        return { success: false, message: errMsg };
      }

      return { success: true, employeeId: data.employee_id, message: data.message };
    } catch (error) {
      console.log('Registration Error:', error.message);
      return { success: false, message: error.message || 'Unable to connect to backend server' };
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout, API_BASE_URL }}>
      {children}
    </AuthContext.Provider>
  );
};
