import React, { useState, useContext } from 'react';
import { View, Text, TextInput, Button, StyleSheet, TouchableOpacity } from 'react-native';
import { AuthContext } from '../context/AuthContext';

export default function LoginScreen() {
  const { login } = useContext(AuthContext);
  const [employeeId, setEmployeeId] = useState('EMP-1001');
  const [role, setRole] = useState('employee'); // 'employee' or 'manager'
  const [department, setDepartment] = useState('IT Operations');

  const handleLogin = () => {
    login({
      id: employeeId,
      name: role === 'manager' ? 'Jane Doe (Manager)' : 'John Doe (Employee)',
      role: role,
      department: department,
    });
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>HRIS Portal</Text>
      
      <Text style={styles.label}>Employee ID</Text>
      <TextInput style={styles.input} value={employeeId} onChangeText={setEmployeeId} />

      <Text style={styles.label}>Department</Text>
      <TextInput style={styles.input} value={department} onChangeText={setDepartment} />

      <Text style={styles.label}>Select Role (RBAC Simulation):</Text>
      <View style={styles.roleContainer}>
        <TouchableOpacity
          style={[styles.roleButton, role === 'employee' && styles.selectedRole]}
          onPress={() => setRole('employee')}
        >
          <Text style={styles.roleText}>Employee</Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[styles.roleButton, role === 'manager' && styles.selectedRole]}
          onPress={() => setRole('manager')}
        >
          <Text style={styles.roleText}>Manager</Text>
        </TouchableOpacity>
      </View>

      <Button title="Sign In" onPress={handleLogin} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyStyle: 'center', padding: 20, backgroundColor: '#f5f5f5' },
  title: { fontSize: 28, fontWeight: 'bold', marginBottom: 24, textAlign: 'center' },
  label: { fontSize: 14, fontWeight: '600', marginBottom: 6, color: '#333' },
  input: { backgroundColor: '#fff', padding: 12, borderRadius: 8, marginBottom: 16, borderWidth: 1, borderColor: '#ddd' },
  roleContainer: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 24 },
  roleButton: { flex: 1, padding: 12, marginHorizontal: 4, borderWidth: 1, borderColor: '#ccc', borderRadius: 8, alignItems: 'center' },
  selectedRole: { backgroundColor: '#007AFF', borderColor: '#007AFF' },
  roleText: { color: '#000', fontWeight: 'bold' },
});
