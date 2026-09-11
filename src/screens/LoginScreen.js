import React, { useState, useContext } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native';
import { AuthContext } from '../context/AuthContext';

export default function LoginScreen() {
  const { login } = useContext(AuthContext);
  const [employeeId, setEmployeeId] = useState('3286');
  const [department, setDepartment] = useState('IT Operations');
  const [password, setPassword] = useState('password123');
  const [role, setRole] = useState('employee');
  const [submitting, setSubmitting] = useState(false);

  const handleLogin = async () => {
    if (!employeeId.trim() || !password.trim()) {
      alert('Please enter both Employee ID and Password');
      return;
    }
    setSubmitting(true);
    await login(employeeId, role, password);
    setSubmitting(false);
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>HRIS Portal</Text>

      <View style={styles.inputGroup}>
        <Text style={styles.label}>Employee ID</Text>
        <TextInput
          style={styles.input}
          value={employeeId}
          onChangeText={setEmployeeId}
          placeholder="Enter Employee ID"
          autoCapitalize="none"
        />
      </View>

      <View style={styles.inputGroup}>
        <Text style={styles.label}>Password</Text>
        <TextInput
          style={styles.input}
          value={password}
          onChangeText={setPassword}
          placeholder="Enter Password"
          secureTextEntry
        />
      </View>

      <View style={styles.inputGroup}>
        <Text style={styles.label}>Department</Text>
        <TextInput
          style={styles.input}
          value={department}
          onChangeText={setDepartment}
          placeholder="Enter Department"
        />
      </View>

      <Text style={styles.label}>Select Role (RBAC Simulation):</Text>
      <View style={styles.roleContainer}>
        <TouchableOpacity
          style={[styles.roleBtn, role === 'employee' && styles.roleBtnActive]}
          onPress={() => setRole('employee')}
        >
          <Text style={[styles.roleBtnText, role === 'employee' && styles.roleBtnTextActive]}>Employee</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.roleBtn, role === 'manager' && styles.roleBtnActive]}
          onPress={() => setRole('manager')}
        >
          <Text style={[styles.roleBtnText, role === 'manager' && styles.roleBtnTextActive]}>Manager</Text>
        </TouchableOpacity>
      </View>

      <TouchableOpacity style={styles.submitBtn} onPress={handleLogin} disabled={submitting}>
        {submitting ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.submitBtnText}>SIGN IN</Text>
        )}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, justifyContent: 'center', backgroundColor: '#f8fafc' },
  title: { fontSize: 28, fontWeight: 'bold', textAlign: 'center', marginBottom: 24, color: '#0f172a' },
  inputGroup: { marginBottom: 16 },
  label: { fontSize: 14, color: '#475569', marginBottom: 6, fontWeight: '600' },
  input: { backgroundColor: '#ffffff', borderWidth: 1, borderColor: '#cbd5e1', padding: 12, borderRadius: 8, fontSize: 16 },
  roleContainer: { flexDirection: 'row', gap: 12, marginBottom: 24, marginTop: 6 },
  roleBtn: { flex: 1, padding: 12, borderRadius: 8, borderWidth: 1, borderColor: '#cbd5e1', alignItems: 'center', backgroundColor: '#ffffff' },
  roleBtnActive: { backgroundColor: '#2563eb', borderColor: '#2563eb' },
  roleBtnText: { color: '#475569', fontWeight: 'bold' },
  roleBtnTextActive: { color: '#ffffff' },
  submitBtn: { backgroundColor: '#2563eb', padding: 14, borderRadius: 8, alignItems: 'center' },
  submitBtnText: { color: '#ffffff', fontWeight: 'bold', fontSize: 16 },
});
