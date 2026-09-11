import React, { useState, useEffect, useContext } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, Alert, Linking, ScrollView, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { AuthContext } from '../context/AuthContext';

export default function DashboardScreen({ navigation }) {
  const { user, logout, API_BASE_URL } = useContext(AuthContext);
  const [loading, setLoading] = useState(false);
  const [initialSync, setInitialSync] = useState(true);
  const [lastPunch, setLastPunch] = useState(null);
  
  // Shift Timer State
  const [isClockedIn, setIsClockedIn] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    fetchActivePunchState();
  }, []);

  useEffect(() => {
    let interval = null;
    if (isClockedIn) {
      interval = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
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
            timestamp: new Date(data.clock_in_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            address: data.last_punch.address || 'Recorded Location',
            lat: data.last_punch.latitude,
            lng: data.last_punch.longitude,
          });
        } else if (data.last_punch) {
          setIsClockedIn(false);
          setLastPunch({
            type: data.last_punch.punch_type,
            timestamp: new Date(data.last_punch.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            address: data.last_punch.address || 'Recorded Location',
            lat: data.last_punch.latitude,
            lng: data.last_punch.longitude,
          });
        }
      }
    } catch (error) {
      console.log('Error syncing shift state:', error);
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
      Alert.alert('Permission Denied', 'Location permission is required.');
      return null;
    }

    setLoading(true);
    try {
      let location = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High });
      let addressStr = 'Location Captured';
      try {
        let geocode = await Location.reverseGeocodeAsync({
          latitude: location.coords.latitude,
          longitude: location.coords.longitude,
        });
        if (geocode && geocode.length > 0) {
          const item = geocode[0];
          addressStr = [item.street, item.city || item.subregion].filter(Boolean).join(', ');
        }
      } catch (e) {
        addressStr = `${location.coords.latitude.toFixed(4)}, ${location.coords.longitude.toFixed(4)}`;
      }
      setLoading(false);
      return { ...location.coords, address: addressStr };
    } catch (error) {
      setLoading(false);
      Alert.alert('Error', 'Unable to fetch location.');
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

      if (!response.ok) throw new Error('Failed to record punch');

      const data = await response.json();
      const punchTime = new Date(data.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      setLastPunch({
        type: punchType,
        timestamp: punchTime,
        address: coordsData.address,
        lat: coordsData.latitude,
        lng: coordsData.longitude,
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

  const handleActionToggle = async () => {
    const coordsData = await requestAndGetLocation();
    if (coordsData) {
      await submitPunchToBackend(isClockedIn ? 'CLOCK_OUT' : 'CLOCK_IN', coordsData);
    }
  };

  if (initialSync) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#2563eb" />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      {/* Header Profile Greeting */}
      <View style={styles.headerRow}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{user.name ? user.name.charAt(0) : 'E'}</Text>
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.greetingText}>Good day, {user.name || 'Employee'}</Text>
          <Text style={styles.subGreeting}>{user.position || 'Staff'} · {user.department}</Text>
        </View>
        <TouchableOpacity style={styles.logoutIconButton} onPress={logout}>
          <Ionicons name="log-out-outline" size={22" color="#64748b" />
        </TouchableOpacity>
      </View>

      {/* Connecteams Style Quick Action Modules */}
      <View style={styles.quickGrid}>
        <TouchableOpacity style={[styles.gridCard, { backgroundColor: '#eff6ff' }]} onPress={() => navigation.navigate('Timesheet')}>
          <View style={[styles.gridIconCircle, { backgroundColor: '#dbeafe' }]}>
            <Ionicons name="time" size={20} color="#2563eb" />
          </View>
          <Text style={styles.gridLabel}>Time Clock</Text>
        </TouchableOpacity>

        <TouchableOpacity style={[styles.gridCard, { backgroundColor: '#f0fdf4' }]} onPress={() => navigation.navigate('Timesheet')}>
          <View style={[styles.gridIconCircle, { backgroundColor: '#dcfce7' }]}>
            <Ionicons name="calendar" size={20} color="#166534" />
          </View>
          <Text style={styles.gridLabel}>Timesheet</Text>
        </TouchableOpacity>

        {user.role === 'manager' && (
          <TouchableOpacity style={[styles.gridCard, { backgroundColor: '#fef2f2' }]} onPress={() => navigation.navigate('Manager')}>
            <View style={[styles.gridIconCircle, { backgroundColor: '#fecaca' }]}>
              <Ionicons name="people" size={20} color="#991b1b" />
            </View>
            <Text style={styles.gridLabel}>Oversight</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* Connecteams Minimal Active Shift Widget */}
      <View style={[styles.shiftCard, isClockedIn ? styles.shiftActiveCard : styles.shiftInactiveCard]}>
        <Text style={[styles.timerDisplay, isClockedIn ? styles.timerActiveText : styles.timerInactiveText]}>
          {formatTimer(elapsedSeconds)}
        </Text>
        
        <Text style={styles.shiftDetails}>
          {user.department} · {user.position || 'Staff'} {lastPunch ? `· Started at ${lastPunch.timestamp}` : ''}
        </Text>

        {lastPunch && (
          <View style={styles.locationPill}>
            <Ionicons name="location-sharp" size={13} color="#64748b" />
            <Text style={styles.locationPillText} numberOfLines={1}>{lastPunch.address}</Text>
          </View>
        )}

        <TouchableOpacity
          style={[styles.actionButton, isClockedIn ? styles.actionOutButton : styles.actionInButton]}
          onPress={handleActionToggle}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color={isClockedIn ? "#991b1b" : "#ffffff"} />
          ) : (
            <Text style={[styles.actionButtonText, isClockedIn ? styles.actionOutText : styles.actionInText]}>
              {isClockedIn ? 'CLOCK OUT' : 'CLOCK IN'}
            </Text>
          )}
        </TouchableOpacity>
      </View>

      {/* Connecteams Style Weekly Summary Chart Widget */}
      <View style={styles.sectionCard}>
        <Text style={styles.sectionTitle}>Weekly Hours</Text>
        
        <View style={styles.chartRow}>
          {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day, idx) => {
            const isFilled = idx < 4; // Simulated current week days worked
            return (
              <View key={day} style={styles.barColumn}>
                <View style={styles.barTrack}>
                  <View style={[styles.barFill, { height: isFilled ? '80%' : '0%' }]} />
                </View>
                <Text style={styles.barLabel}>{day}</Text>
              </View>
            );
          })}
        </View>

        <View style={styles.chartFooter}>
          <Text style={styles.chartFooterLabel}>Total hours this week</Text>
          <Text style={styles.chartFooterValue}>32:15</Text>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc', padding: 16 },
  centerContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#f8fafc' },
  headerRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 20, gap: 12 },
  avatar: { width: 44, height: 44, borderRadius: 22, backgroundColor: '#2563eb', justifyContent: 'center', alignItems: 'center' },
  avatarText: { color: '#ffffff', fontWeight: 'bold', fontSize: 18 },
  greetingText: { fontSize: 18, fontWeight: '700', color: '#0f172a' },
  subGreeting: { fontSize: 12, color: '#64748b' },
  logoutIconButton: { padding: 8 },
  quickGrid: { flexDirection: 'row', gap: 10, marginBottom: 16 },
  gridCard: { flex: 1, padding: 12, borderRadius: 12, alignItems: 'center', borderWidth: 1, borderColor: '#f1f5f9' },
  gridIconCircle: { width: 36, height: 36, borderRadius: 18, justifyContent: 'center', alignItems: 'center', marginBottom: 6 },
  gridLabel: { fontSize: 11, fontWeight: '600', color: '#334155' },
  shiftCard: { borderRadius: 16, padding: 20, alignItems: 'center', marginBottom: 16, borderWidth: 1, borderColor: '#e2e8f0' },
  shiftActiveCard: { backgroundColor: '#eff6ff', borderColor: '#bfdbfe' },
  shiftInactiveCard: { backgroundColor: '#ffffff' },
  timerDisplay: { fontSize: 38, fontWeight: '800', marginBottom: 4, fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace' },
  timerActiveText: { color: '#2563eb' },
  timerInactiveText: { color: '#475569' },
  shiftDetails: { fontSize: 12, color: '#64748b', marginBottom: 8, textAlign: 'center' },
  locationPill: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: '#ffffff', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12, marginBottom: 16, borderWidth: 1, borderColor: '#e2e8f0' },
  locationPillText: { fontSize: 12, color: '#475569' },
  actionButton: { width: '100%', paddingVertical: 14, borderRadius: 10, alignItems: 'center' },
  actionInButton: { backgroundColor: '#2563eb' },
  actionOutButton: { backgroundColor: '#ffffff', borderWidth: 1, borderColor: '#fecaca' },
  actionButtonText: { fontWeight: '700', fontSize: 15 },
  actionInText: { color: '#ffffff' },
  actionOutText: { color: '#dc2626' },
  sectionCard: { backgroundColor: '#ffffff', borderRadius: 16, padding: 16, borderWidth: 1, borderColor: '#f1f5f9', marginBottom: 24 },
  sectionTitle: { fontSize: 15, fontWeight: '700', color: '#0f172a', marginBottom: 16 },
  chartRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end', height: 100, marginBottom: 16, paddingHorizontal: 8 },
  barColumn: { alignItems: 'center', gap: 6 },
  barTrack: { width: 24, height: 80, backgroundColor: '#f1f5f9', borderRadius: 6, justifyContent: 'flex-end', overflow: 'hidden' },
  barFill: { width: '100%', backgroundColor: '#3b82f6', borderRadius: 6 },
  barLabel: { fontSize: 11, color: '#94a3b8', fontWeight: '500' },
  chartFooter: { flexDirection: 'row', justifyContent: 'space-between', paddingTop: 12, borderTopWidth: 1, borderTopColor: '#f1f5f9' },
  chartFooterLabel: { fontSize: 13, color: '#64748b', fontWeight: '500' },
  chartFooterValue: { fontSize: 13, fontWeight: '700', color: '#0f172a' },
});
