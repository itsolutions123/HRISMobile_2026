import React, { useContext } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { AuthContext } from '../context/AuthContext';

export default function ManagerScreen() {
  const { user } = useContext(AuthContext);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Manager Approvals Dashboard</Text>
      <Text style={styles.subtitle}>Filtered by Department: {user.department}</Text>
      <View style={styles.card}>
        <Text style={styles.cardText}>Pending Timesheets: 0</Text>
        <Text style={styles.cardText}>Active Field Employees: 3</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, backgroundColor: '#fff' },
  title: { fontSize: 20, fontWeight: 'bold', color: '#2e7d32' },
  subtitle: { fontSize: 14, color: '#666', marginBottom: 15 },
  card: { padding: 15, backgroundColor: '#f0f4f8', borderRadius: 8 },
  cardText: { fontSize: 16, marginVertical: 4 },
});
