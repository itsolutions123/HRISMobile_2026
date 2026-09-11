import React, { useState, useEffect, useContext } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, Alert, Linking, ScrollView, Platform } from 'react-native';
import { WebView } from 'react-native-webview';
import * as Location from 'expo-location';
import { AuthContext } from '../context/AuthContext';

export default function DashboardScreen({ navigation }) {
  const { user, logout, API_BASE_URL } = useContext(AuthContext);
  const [loading, setLoading] = useState(false);
  const [initialSync, setInitialSync] = useState(true);
  const [lastPunch, setLastPunch] = useState(null);
  
  // Timer State
  const [isClockedIn, setIsClockedIn] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // Fetch active punch state on component mount / re-login
  useEffect(() => {
    fetchActivePunchState();
  }, []);

  // Timer Ticker
  useEffect(() => {
    let interval = null;
    if (isClockedIn) {
      interval = setInterval(() => {
        setElapsedSeconds((prev) => {
          if (prev >= 20 * 3600) {
            Alert.alert("Auto Clock-Out", "Your shift exceeded 20 hours and was automatically ended.");
            setIsClockedIn(false);
            return 0;
          }
          return prev + 1;
        });
      }, 1000);
    } else {
      clearInterval(interval);
    }
    return () => clearInterval(interval);
  }, [isClockedIn]);

  const fetchActivePunchState = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/punch/active/${user.employee_id}`);
      if (response.ok) {
        const data = await response.json();
        if (data.is_clocked_in) {
          setIsClockedIn(true);
          setElapsedSeconds(data.elapsed_seconds);
          setLastPunch({
            type: 'CLOCK_IN',
            timestamp: new Date(data.clock_in_time).toLocaleTimeString(),
            lat: data.last_punch.latitude,
            lng: data.last_punch.longitude,
            address: data.last_punch.address || 'Recorded Location',
          });
        } else if (data.last_punch) {
          setIsClockedIn(false);
          setLastPunch({
            type: data.last_punch.punch_type,
            timestamp: new Date(data.last_punch.timestamp).toLocaleTimeString(),
            lat: data.last_punch.latitude,
            lng: data.last_punch.longitude,
            address: data.last_punch.address || 'Recorded Location',
          });
        }
      }
    } catch (error) {
      console.log('Error fetching active punch status:', error);
    } finally {
      setInitialSync(false);
    }
  };

  const formatTimer = (totalSeconds) => {
    const hrs = Math.floor(totalSeconds / 3600).toString().padStart(2, '0');
    const mins = Math.floor((totalSeconds % 3600) / 60).toString().padStart(2, '0');
    const secs = (totalSeconds % 60).toString().padStart(2, '0');
    return `${hrs}:${mins}:${secs}`;
  };

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

      let addressStr = 'Unknown Location';
      try {
        let geocode = await Location.reverseGeocodeAsync({
          latitude: location.coords.latitude,
          longitude: location.coords.longitude,
        });

        if (geocode && geocode.length > 0) {
          const item = geocode[0];
          const parts = [item.streetNumber, item.street, item.subregion || item.city, item.region];
          addressStr = parts.filter(Boolean).join(', ');
        }
      } catch (e) {
        addressStr = `${location.coords.latitude.toFixed(5)}, ${location.coords.longitude.toFixed(5)}`;
      }

      setLoading(false);
      return { ...location.coords, address: addressStr };
    } catch (error) {
      setLoading(false);
      Alert.alert('Error', 'Unable to fetch current location.');
      return null;
    }
  };

  const submitPunchToBackend = async (punchType, coordsData) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/punch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          employee_id: user.employee_id,
          punch_type: punchType,
          latitude: coordsData.latitude,
          longitude: coordsData.longitude,
          accuracy: coordsData.accuracy || 0,
          address: coordsData.address,
        }),
      });

      if (!response.ok) throw new Error('Failed to persist punch to server');

      const data = await response.json();
      const punchTime = new Date(data.timestamp).toLocaleTimeString();

      setLastPunch({
        type: punchType,
        timestamp: punchTime,
        lat: coordsData.latitude,
        lng: coordsData.longitude,
        address: coordsData.address,
      });

      if (punchType === 'CLOCK_IN') {
        setIsClockedIn(true);
        setElapsedSeconds(0);
      } else {
        setIsClockedIn(false);
        setElapsedSeconds(0);
      }
    } catch (error) {
      Alert.alert('Sync Error', error.message);
    }
  };

  const handleClockIn = async () => {
    const coordsData = await requestAndGetLocation();
    if (coordsData) await submitPunchToBackend('CLOCK_IN', coordsData);
  };

  const handleClockOut = async () => {
    const coordsData = await requestAndGetLocation();
    if (coordsData) await submitPunchToBackend('CLOCK_OUT', coordsData);
  };

  const openGoogleMaps = () => {
    if (!lastPunch) return;
    const url = `https://www.google.com/maps/search/?api=1&query=${lastPunch.lat},${lastPunch.lng}`;
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
          src="https://maps.google.com/maps?q=loc:${lat}+${lng}&z=18&output=embed"
          allowfullscreen>
        </iframe>
      </body>
    </html>
  `;

  if (initialSync) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" color="#2563eb" />
        <Text style={{ marginTop: 10, color: '#475569' }}>Syncing Shift Status...</Text>
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.scrollContainer} showsVerticalScrollIndicator={false}>
      <View style={styles.profileCard}>
        <Text style={styles.welcome}>Welcome, {user.name}</Text>
        <Text style={styles.profileText}>Position: <Text style={styles.boldText}>{user.position || 'Staff'}</Text></Text>
        <Text style={styles.profileText}>Department: <Text style={styles.boldText}>{user.department}</Text></Text>
        <Text style={styles.profileText}>Role: <Text style={styles.boldText}>{user.role.toUpperCase()}</Text></Text>
      </View>

      {/* Live Persistent Shift Timer */}
      <View style={[styles.timerCard, isClockedIn ? styles.timerActive : styles.timerInactive]}>
        <Text style={styles.timerLabel}>{isClockedIn ? 'ON DUTY - SHIFT TIMER' : 'OFF DUTY'}</Text>
        <Text style={styles.timerValue}>{formatTimer(elapsedSeconds)}</Text>
      </View>

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
            <TouchableOpacity 
              style={[styles.clockInBtn, isClockedIn && styles.disabledBtn]} 
              onPress={handleClockIn} 
              disabled={isClockedIn}
            >
              <Text style={styles.btnText}>CLOCK IN</Text>
            </TouchableOpacity>
            
            <TouchableOpacity 
              style={[styles.clockOutBtn, !isClockedIn && styles.disabledBtn]} 
              onPress={handleClockOut} 
              disabled={!isClockedIn}
            >
              <Text style={styles.btnText}>CLOCK OUT</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>

      {lastPunch && (
        <View style={styles.punchCard}>
          <Text style={styles.punchTitle}>Last Punch: {lastPunch.type} ({lastPunch.timestamp})</Text>
          <Text style={styles.locationText}>📍 Location: <Text style={styles.boldText}>{lastPunch.address}</Text></Text>

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
  profileCard: { backgroundColor: '#ffffff', padding: 16, borderRadius: 12, marginBottom: 12, borderWidth: 1, borderColor: '#e5e7eb', elevation: 1 },
  welcome: { fontSize: 20, fontWeight: 'bold', color: '#111827', marginBottom: 4 },
  profileText: { fontSize: 13, color: '#4b5563', marginTop: 2 },
  boldText: { fontWeight: 'bold', color: '#111827' },
  timerCard: { padding: 16, borderRadius: 12, alignItems: 'center', marginBottom: 12, elevation: 2 },
  timerActive: { backgroundColor: '#1e3a8a' },
  timerInactive: { backgroundColor: '#374151' },
  timerLabel: { color: '#93c5fd', fontSize: 12, fontWeight: 'bold', letterSpacing: 1 },
  timerValue: { color: '#ffffff', fontSize: 36, fontWeight: 'bold', marginTop: 4, fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace' },
  managerBtn: { backgroundColor: '#2e7d32', padding: 12, borderRadius: 8, alignItems: 'center', marginBottom: 12 },
  managerBtnText: { color: '#fff', fontWeight: 'bold', fontSize: 14 },
  actionCard: { backgroundColor: '#ffffff', padding: 16, borderRadius: 12, marginBottom: 12, elevation: 2, borderWidth: 1, borderColor: '#e5e7eb' },
  buttonGroup: { gap: 10 },
  clockInBtn: { backgroundColor: '#15803d', paddingVertical: 14, borderRadius: 8, alignItems: 'center' },
  clockOutBtn: { backgroundColor: '#b91c1c', paddingVertical: 14, borderRadius: 8, alignItems: 'center' },
  disabledBtn: { opacity: 0.4 },
  btnText: { color: '#ffffff', fontWeight: 'bold', fontSize: 15, letterSpacing: 0.5 },
  punchCard: { backgroundColor: '#ffffff', padding: 14, borderRadius: 12, marginBottom: 12, borderWidth: 1, borderColor: '#e5e7eb', elevation: 2 },
  punchTitle: { fontWeight: 'bold', marginBottom: 4, fontSize: 14, color: '#1f2937' },
  locationText: { fontSize: 13, color: '#374151', marginBottom: 10 },
  mapFrame: { height: 220, width: '100%', borderRadius: 8, overflow: 'hidden', borderWidth: 1, borderColor: '#d1d5db', marginBottom: 12 },
  map: { width: '100%', height: '100%' },
  extMapBtn: { backgroundColor: '#2563eb', paddingVertical: 12, borderRadius: 8, alignItems: 'center' },
  extMapBtnText: { color: '#ffffff', fontWeight: 'bold', fontSize: 13 },
  logoutBtn: { backgroundColor: '#4b5563', paddingVertical: 12, borderRadius: 8, alignItems: 'center', marginTop: 10 },
  logoutBtnText: { color: '#ffffff', fontWeight: 'bold', fontSize: 14 },
});
