import React, { useState, useContext } from 'react';
import { View, Text, Button, StyleSheet, ActivityIndicator, Alert } from 'react-native';
import * as Location from 'expo-location';
import { AuthContext } from '../context/AuthContext';

export default function DashboardScreen({ navigation }) {
  const { user, logout } = useContext(AuthContext);
  const [loading, setLoading] = useState(false);
  const [lastPunch, setLastPunch] = useState(null);

  const requestAndGetLocation = async () => {
    let { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission Denied', 'Location permission is required to clock in/out.');
      return null;
    }

    setLoading(true);
    try {
      let location = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.High,
      });
      setLoading(false);
      return location.coords;
    } catch (error) {
      setLoading(false);
      Alert.alert('Error', 'Unable to fetch current location.');
      return null;
    }
  };

  const handleClockIn = async () => {
    const coords = await requestAndGetLocation();
    if (coords) {
      const punchData = {
        type: 'CLOCK_IN',
        timestamp: new Date().toLocaleTimeString(),
        lat: coords.latitude,
        lng: coords.longitude,
        accuracy: coords.accuracy,
      };
      setLastPunch(punchData);
      Alert.alert('Clocked In Successfully', `Lat: ${coords.latitude}\nLng: ${coords.longitude}`);
    }
  };

  const handleClockOut = async () => {
    const coords = await requestAndGetLocation();
    if (coords) {
      const punchData = {
        type: 'CLOCK_OUT',
        timestamp: new Date().toLocaleTimeString(),
        lat: coords.latitude,
        lng: coords.longitude,
        accuracy: coords.accuracy,
      };
      setLastPunch(punchData);
      Alert.alert('Clocked Out Successfully', `Lat: ${coords.latitude}\nLng: ${coords.longitude}`);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.welcome}>Welcome, {user.name}</Text>
      <Text style={styles.subtext}>Dept: {user.department} | Role: {user.role.toUpperCase()}</Text>

      {user.role === 'manager' && (
        <View style={styles.managerBanner}>
          <Button title="Open Manager Dashboard" onPress={() => navigation.navigate('Manager')} color="#2e7d32" />
        </View>
      )}

      <View style={styles.actionCard}>
        {loading ? (
          <ActivityIndicator size="large" color="#007AFF" />
        ) : (
          <View style={styles.buttonGroup}>
            <Button title="Clock In" onPress={handleClockIn} color="#1b5e20" />
            <View style={{ height: 12 }} />
            <Button title="Clock Out" onPress={handleClockOut} color="#b71c1c" />
          </View>
        )}
      </View>

      {lastPunch && (
        <View style={styles.punchInfo}>
          <Text style={styles.punchTitle}>Last Recorded Punch:</Text>
          <Text>Type: {lastPunch.type}</Text>
          <Text>Time: {lastPunch.timestamp}</Text>
          <Text>Coordinates: {lastPunch.lat.toFixed(5)}, {lastPunch.lng.toFixed(5)}</Text>
          <Text>Accuracy: ~{Math.round(lastPunch.accuracy)} meters</Text>
        </View>
      )}

      <View style={styles.footer}>
        <Button title="Sign Out" onPress={logout} color="#555" />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, backgroundColor: '#f9f9f9' },
  welcome: { fontSize: 22, fontWeight: 'bold', color: '#111' },
  subtext: { fontSize: 14, color: '#666', marginBottom: 20 },
  managerBanner: { marginBottom: 20, backgroundColor: '#e8f5e9', padding: 10, borderRadius: 8 },
  actionCard: { backgroundColor: '#fff', padding: 20, borderRadius: 12, marginBottom: 20, elevation: 2 },
  buttonGroup: { justifyContent: 'space-between' },
  punchInfo: { backgroundColor: '#eef2f5', padding: 15, borderRadius: 8 },
  punchTitle: { fontWeight: 'bold', marginBottom: 6 },
  footer: { marginTop: 'auto', paddingTop: 20 },
});
