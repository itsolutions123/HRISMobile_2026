import React, { useState, useEffect, useContext } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator, Linking, RefreshControl } from 'react-native';
import { AuthContext } from '../context/AuthContext';

export default function ManagerScreen() {
  const { user, API_BASE_URL } = useContext(AuthContext);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [punches, setPunches] = useState([]);

  const fetchDepartmentPunches = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/manager/punches?department=${encodeURIComponent(user.department)}`);
      if (response.ok) {
        const data = await response.json();
        setPunches(data.punches || []);
      }
    } catch (error) {
      console.log('Error fetching manager punches:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDepartmentPunches();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    fetchDepartmentPunches();
  };

  const openGoogleMaps = (lat, lng) => {
    const url = `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`;
    Linking.openURL(url);
  };

  const renderPunchItem = ({ item }) => (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <Text style={styles.employeeId}>Employee ID: {item.employee_id}</Text>
        <Text style={[styles.badge, item.punch_type === 'CLOCK_IN' ? styles.badgeIn : styles.badgeOut]}>
          {item.punch_type}
        </Text>
      </View>
      <Text style={styles.timestamp}>Time: {new Date(item.timestamp).toLocaleString()}</Text>
      <Text style={styles.address}>📍 {item.address || 'GPS Location Captured'}</Text>

      <TouchableOpacity style={styles.mapLink} onPress={() => openGoogleMaps(item.latitude, item.longitude)}>
        <Text style={styles.mapLinkText}>View Pin on Google Maps ({item.latitude.toFixed(4)}, {item.longitude.toFixed(4)})</Text>
      </TouchableOpacity>
    </View>
  );

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Department Oversight: {user.department}</Text>
      <Text style={styles.subtitle}>Real-time employee clock-in and GPS logs</Text>

      {loading ? (
        <ActivityIndicator size="large" color="#2563eb" style={{ marginTop: 20 }} />
      ) : (
        <FlatList
          data={punches}
          keyExtractor={(item) => item.id.toString()}
          renderItem={renderPunchItem}
          contentContainerStyle={{ paddingBottom: 20 }}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
          ListEmptyComponent={<Text style={styles.emptyText}>No attendance records found for this department.</Text>}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#f8fafc' },
  title: { fontSize: 20, fontWeight: 'bold', color: '#0f172a' },
  subtitle: { fontSize: 13, color: '#64748b', marginBottom: 16 },
  card: { backgroundColor: '#ffffff', padding: 14, borderRadius: 10, marginBottom: 12, borderWidth: 1, borderColor: '#e2e8f0', elevation: 1 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  employeeId: { fontWeight: 'bold', fontSize: 15, color: '#1e293b' },
  badge: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6, fontWeight: 'bold', fontSize: 11, overflow: 'hidden' },
  badgeIn: { backgroundColor: '#dcfce7', color: '#15803d' },
  badgeOut: { backgroundColor: '#fee2e2', color: '#b91c1c' },
  timestamp: { fontSize: 13, color: '#475569', marginBottom: 4 },
  address: { fontSize: 13, color: '#334155', marginBottom: 10 },
  mapLink: { backgroundColor: '#eff6ff', padding: 8, borderRadius: 6, alignItems: 'center', borderWidth: 1, borderColor: '#bfdbfe' },
  mapLinkText: { color: '#2563eb', fontWeight: 'bold', fontSize: 12 },
  emptyText: { textAlign: 'center', color: '#94a3b8', marginTop: 40, fontSize: 14 },
});
