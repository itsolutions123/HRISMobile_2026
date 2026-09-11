import React, { useState, useContext } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, Alert, Linking, ScrollView } from 'react-native';
import { WebView } from 'react-native-webview';
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
    const url = `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`;
    Linking.openURL(url);
  };

  const generateIframeHTML = (lat, lng) => `
    <!DOCTYPE html>
    <html>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
        <style>
          html, body { height: 100%; width: 100%; margin: 0; padding: 0; overflow: hidden; background: #e5e7eb; }
          iframe { width: 100%; height: 100%; border: 0; }
        </style>
      </head>
      <body>
        <iframe
          src="https://maps.google.com/maps?q=${lat},${lng}&z=16&output=embed"
          allowfullscreen>
        </iframe>
      </body>
    </html>
  `;

  return (
    <ScrollView contentContainerStyle={styles.scrollContainer} showsVerticalScrollIndicator={false}>
      <Text style={styles.welcome}>Welcome, {user.name}</Text>
      <Text style={styles.subtext}>Dept: {user.department} | Role: {user.role.toUpperCase()}</Text>

      {user.role === 'manager' && (
        <TouchableOpacity style={styles.managerBtn} onPress={() => navigation.navigate('Manager')}>
          <Text style={styles.managerBtnText}>Open Manager Dashboard</Text>
        </TouchableOpacity>
      )}

      <View style={styles.actionCard}>
        {loading ? (
          <ActivityIndicator size="large" color="#007AFF" />
        ) : (
          <View style={styles.buttonGroup}>
            <TouchableOpacity style={styles.clockInBtn} onPress={handleClockIn}>
              <Text style={styles.btnText}>CLOCK IN</Text>
            </TouchableOpacity>
            
            <TouchableOpacity style={styles.clockOutBtn} onPress={handleClockOut}>
              <Text style={styles.btnText}>CLOCK OUT</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>

      {lastPunch && (
        <View style={styles.punchCard}>
          <Text style={styles.punchTitle}>Last Punch: {lastPunch.type} ({lastPunch.timestamp})</Text>

          <View style={styles.mapFrame}>
            <WebView
              originWhitelist={['*']}
              source={{ html: generateIframeHTML(lastPunch.lat, lastPunch.lng) }}
              style={styles.map}
              javaScriptEnabled={true}
              domStorageEnabled={true}
              scrollEnabled={false}
            />
          </View>

          <TouchableOpacity style={styles.extMapBtn} onPress={openGoogleMaps}>
            <Text style={styles.extMapBtnText}>OPEN IN GOOGLE MAPS APP</Text>
          </TouchableOpacity>
        </View>
      )}

      <TouchableOpacity style={styles.logoutBtn} onPress={logout}>
        <Text style={styles.logoutBtnText}>SIGN OUT</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scrollContainer: { flexGrow: 1, padding: 16, backgroundColor: '#f4f6f8', paddingBottom: 40 },
  welcome: { fontSize: 20, fontWeight: 'bold', color: '#111827' },
  subtext: { fontSize: 13, color: '#6b7280', marginBottom: 16 },
  managerBtn: { backgroundColor: '#2e7d32', padding: 12, borderRadius: 8, alignItems: 'center', marginBottom: 16 },
  managerBtnText: { color: '#fff', fontWeight: 'bold', fontSize: 14 },
  actionCard: { backgroundColor: '#ffffff', padding: 16, borderRadius: 12, marginBottom: 16, elevation: 2, borderWidth: 1, borderColor: '#e5e7eb' },
  buttonGroup: { gap: 10 },
  clockInBtn: { backgroundColor: '#15803d', paddingVertical: 14, borderRadius: 8, alignItems: 'center' },
  clockOutBtn: { backgroundColor: '#b91c1c', paddingVertical: 14, borderRadius: 8, alignItems: 'center' },
  btnText: { color: '#ffffff', fontWeight: 'bold', fontSize: 15, letterSpacing: 0.5 },
  punchCard: { backgroundColor: '#ffffff', padding: 14, borderRadius: 12, marginBottom: 16, borderWidth: 1, borderColor: '#e5e7eb', elevation: 2 },
  punchTitle: { fontWeight: 'bold', marginBottom: 10, fontSize: 14, color: '#1f2937' },
  mapFrame: { height: 220, width: '100%', borderRadius: 8, overflow: 'hidden', borderWidth: 1, borderColor: '#d1d5db', marginBottom: 12 },
  map: { width: '100%', height: '100%' },
  extMapBtn: { backgroundColor: '#2563eb', paddingVertical: 12, borderRadius: 8, alignItems: 'center' },
  extMapBtnText: { color: '#ffffff', fontWeight: 'bold', fontSize: 13 },
  logoutBtn: { backgroundColor: '#4b5563', paddingVertical: 12, borderRadius: 8, alignItems: 'center', marginTop: 10 },
  logoutBtnText: { color: '#ffffff', fontWeight: 'bold', fontSize: 14 },
});
