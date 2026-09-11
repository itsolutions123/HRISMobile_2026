import React, { useState, useContext } from 'react';
import { View, Text, Button, StyleSheet, ActivityIndicator, Alert, Linking, Platform } from 'react-native';
import MapView, { Marker } from 'react-native-maps';
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
      setLastPunch({
        type: 'CLOCK_IN',
        timestamp: new Date().toLocaleTimeString(),
        lat: coords.latitude,
        lng: coords.longitude,
        accuracy: coords.accuracy,
      });
    }
  };

  const handleClockOut = async () => {
    const coords = await requestAndGetLocation();
    if (coords) {
      setLastPunch({
        type: 'CLOCK_OUT',
        timestamp: new Date().toLocaleTimeString(),
        lat: coords.latitude,
        lng: coords.longitude,
        accuracy: coords.accuracy,
      });
    }
  };

  const openGoogleMaps = () => {
    if (!lastPunch) return;
    const { lat, lng } = lastPunch;
    const scheme = Platform.OS === 'ios' ? 'maps:0,0?q=' : 'geo:0,0?q=';
    const latLng = `${lat},${lng}`;
    const label = `HRIS Punch Location (${lastPunch.type})`;
    const url = Platform.select({
      ios: `${scheme}${label}@${latLng}`,
      android: `${scheme}${latLng}(${label})`,
    });

    Linking.openURL(url).catch(() => {
      // Fallback to web browser if map app isn't installed
      Linking.openURL(`https://www.google.com/maps/search/?api=1&query=${lat},${lng}`);
    });
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
            <View style={{ height: 10 }} />
            <Button title="Clock Out" onPress={handleClockOut} color="#b71c1c" />
          </View>
        )}
      </View>

      {lastPunch && (
        <View style={styles.punchInfo}>
          <Text style={styles.punchTitle}>Last Punch: {lastPunch.type} ({lastPunch.timestamp})</Text>

          {/* Embedded Native Map */}
          <View style={styles.mapContainer}>
            <MapView
              style={styles.map}
              initialRegion={{
                latitude: lastPunch.lat,
                longitude: lastPunch.lng,
                latitudeDelta: 0.005,
                longitudeDelta: 0.005,
              }}
            >
              <Marker
                coordinate={{ latitude: lastPunch.lat, longitude: lastPunch.lng }}
                title={lastPunch.type}
                description={`Time: ${lastPunch.timestamp}`}
              />
            </MapView>
          </View>

          <View style={{ marginTop: 10 }}>
            <Button title="Open in Google Maps App" onPress={openGoogleMaps} color="#007AFF" />
          </View>
        </View>
      )}

      <View style={styles.footer}>
        <Button title="Sign Out" onPress={logout} color="#555" />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#f9f9f9' },
  welcome: { fontSize: 22, fontWeight: 'bold', color: '#111' },
  subtext: { fontSize: 14, color: '#666', marginBottom: 12 },
  managerBanner: { marginBottom: 12, backgroundColor: '#e8f5e9', padding: 8, borderRadius: 8 },
  actionCard: { backgroundColor: '#fff', padding: 16, borderRadius: 12, marginBottom: 12, elevation: 2 },
  buttonGroup: { justifyContent: 'space-between' },
  punchInfo: { backgroundColor: '#eef2f5', padding: 12, borderRadius: 8 },
  punchTitle: { fontWeight: 'bold', marginBottom: 8, fontSize: 14 },
  mapContainer: { height: 180, borderRadius: 8, overflow: 'hidden' },
  map: { width: '100%', height: '100%' },
  footer: { marginTop: 'auto', paddingTop: 12 },
});
