import React, { useState, useEffect, useContext } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, ActivityIndicator, Alert, KeyboardAvoidingView, Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { AuthContext } from '../context/AuthContext';

export default function LoginScreen() {
  const { login, API_BASE_URL } = useContext(AuthContext);
  const [employeeId, setEmployeeId] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [department, setDepartment] = useState('Admin');
  const [departmentsList, setDepartmentsList] = useState(['Admin', 'IT Operations', 'Executive', 'Operations', 'Sales']);
  const [showDeptDropdown, setShowDeptDropdown] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadSavedCredentials();
    fetchDynamicDepartments();
  }, []);

  const fetchDynamicDepartments = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/departments`);
      if (response.ok) {
        const data = await response.json();
        if (Array.isArray(data) && data.length > 0) {
          setDepartmentsList(data);
        }
      }
    } catch (e) {
      console.log('Using default department list fallback:', e);
    }
  };

  const loadSavedCredentials = async () => {
    try {
      const savedEmpId = await AsyncStorage.getItem('hris_last_emp_id');
      const savedDept = await AsyncStorage.getItem('hris_last_dept');
      if (savedEmpId) setEmployeeId(savedEmpId);
      if (savedDept) setDepartment(savedDept);
    } catch (e) {
      console.log('Error reading storage:', e);
    }
  };

  const handleLogin = async () => {
    if (!employeeId || !password) {
      Alert.alert('Missing Fields', 'Please enter your Employee ID and Password.');
      return;
    }

    setLoading(true);
    try {
      await AsyncStorage.setItem('hris_last_emp_id', employeeId);
      await AsyncStorage.setItem('hris_last_dept', department);

      const success = await login(employeeId, password, department);
      if (!success) {
        Alert.alert('Authentication Failed', 'Invalid Employee ID, Password, or Department.');
      }
    } catch (error) {
      Alert.alert('Login Error', error.message || 'Unable to connect to HRIS backend server.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.container}>
      <View style={styles.card}>
        <View style={styles.logoBadge}>
          <Ionicons name="shield-checkmark" size={32} color="#ffffff" />
        </View>

        <Text style={styles.title}>HRIS Portal</Text>
        <Text style={styles.subtitle}>Sign in to access your attendance workspace</Text>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>Employee ID</Text>
          <View style={styles.inputWrapper}>
            <Ionicons name="person-outline" size={18} color="#64748b" style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              placeholder="e.g. 3286"
              value={employeeId}
              onChangeText={setEmployeeId}
              autoCapitalize="characters"
            />
          </View>
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>Department Assignment</Text>
          <TouchableOpacity
            style={styles.dropdownTrigger}
            activeOpacity={0.8}
            onPress={() => setShowDeptDropdown(!showDeptDropdown)}
          >
            <Ionicons name="business-outline" size={18} color="#64748b" style={styles.inputIcon} />
            <Text style={styles.dropdownValueText}>{department}</Text>
            <Ionicons name={showDeptDropdown ? "chevron-up" : "chevron-down"} size={18} color="#64748b" />
          </TouchableOpacity>

          {showDeptDropdown && (
            <View style={styles.dropdownMenu}>
              {departmentsList.map((dept) => (
                <TouchableOpacity
                  key={dept}
                  style={[styles.dropdownItem, department === dept && styles.dropdownItemActive]}
                  onPress={() => {
                    setDepartment(dept);
                    setShowDeptDropdown(false);
                  }}
                >
                  <Text style={[styles.dropdownItemText, department === dept && styles.dropdownItemTextActive]}>
                    {dept}
                  </Text>
                  {department === dept && <Ionicons name="checkmark" size={16} color="#2563eb" />}
                </TouchableOpacity>
              ))}
            </View>
          )}
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>Password</Text>
          <View style={styles.inputWrapper}>
            <Ionicons name="lock-closed-outline" size={18} color="#64748b" style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              placeholder="••••••••"
              secureTextEntry={!showPassword}
              value={password}
              onChangeText={setPassword}
            />
            <TouchableOpacity onPress={() => setShowPassword(!showPassword)} style={styles.eyeBtn}>
              <Ionicons name={showPassword ? "eye-off-outline" : "eye-outline"} size={20} color="#64748b" />
            </TouchableOpacity>
          </View>
        </View>

        <TouchableOpacity style={styles.submitBtn} onPress={handleLogin} disabled={loading} activeOpacity={0.85}>
          {loading ? (
            <ActivityIndicator color="#ffffff" />
          ) : (
            <Text style={styles.submitBtnText}>Sign In</Text>
          )}
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc', justifyContent: 'center', padding: 20 },
  card: { backgroundColor: '#ffffff', borderRadius: 20, padding: 24, borderWidth: 1, borderColor: '#f1f5f9', elevation: 3 },
  logoBadge: { width: 56, height: 56, borderRadius: 16, backgroundColor: '#2563eb', justifyContent: 'center', alignItems: 'center', alignSelf: 'center', marginBottom: 12 },
  title: { fontSize: 22, fontWeight: '800', color: '#0f172a', textAlign: 'center' },
  subtitle: { fontSize: 13, color: '#64748b', textAlign: 'center', marginBottom: 24 },
  inputGroup: { marginBottom: 16 },
  label: { fontSize: 12, fontWeight: '700', color: '#475569', marginBottom: 6 },
  inputWrapper: { flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderColor: '#cbd5e1', borderRadius: 10, paddingHorizontal: 12, height: 46, backgroundColor: '#ffffff' },
  inputIcon: { marginRight: 8 },
  eyeBtn: { padding: 4 },
  input: { flex: 1, fontSize: 14, color: '#0f172a' },
  dropdownTrigger: { flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderColor: '#cbd5e1', borderRadius: 10, paddingHorizontal: 12, height: 46, backgroundColor: '#ffffff' },
  dropdownValueText: { flex: 1, fontSize: 14, color: '#0f172a' },
  dropdownMenu: { marginTop: 4, borderWidth: 1, borderColor: '#e2e8f0', borderRadius: 10, backgroundColor: '#ffffff', elevation: 4, overflow: 'hidden' },
  dropdownItem: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 12, paddingHorizontal: 14, borderBottomWidth: 1, borderBottomColor: '#f1f5f9' },
  dropdownItemActive: { backgroundColor: '#eff6ff' },
  dropdownItemText: { fontSize: 13, color: '#334155' },
  dropdownItemTextActive: { color: '#2563eb', fontWeight: '700' },
  submitBtn: { backgroundColor: '#2563eb', height: 48, borderRadius: 10, justifyContent: 'center', alignItems: 'center', marginTop: 8 },
  submitBtnText: { color: '#ffffff', fontWeight: '700', fontSize: 15 },
});
