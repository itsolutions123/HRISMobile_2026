import React, { useState, useEffect, useContext, useCallback, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, Alert, ScrollView, Platform } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import * as Location from 'expo-location';
import { Ionicons } from '@expo/vector-icons';
import { AuthContext } from '../context/AuthContext';

export default function HomeScreen() {
  const { user, logout, API_BASE_URL } = useContext(AuthContext);
  const [isClockedIn, setIsClockedIn] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [loading, setLoading] = useState(false);
  const [fetchingStatus, setFetchingStatus] = useState(true);
  const [locationText, setLocationText] = useState('Fetching GPS location...');

  const timerRef = useRef(null);

  // Request foreground GPS permissions and acquire high-accuracy coordinates
  const getCurrentLocation = async () => {
    try {
      let { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        setLocationText('Location permission denied');
        return { latitude: 14.5764, longitude: 121.0851, address: 'Permission Denied - Default Pasig' };
      }

      let loc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High });
      const lat = loc.coords.latitude;
      const lng = loc.coords.longitude;
      setLocationText(`GPS Active: ${lat.toFixed(4)}, ${lng.toFixed(4)} (±${Math.round(loc.coords.accuracy)}m)`);

      return {
        latitude: lat,
        longitude: lng,
        address: `GPS Pin: ${lat.toFixed(4)}, ${lng.toFixed(4)}`
      };
    } catch (e) {
      setLocationText('Pasig Area Location');
      return { latitude: 14.5764, longitude: 121.0851, address: 'Pasig, Metro Manila' };
    }
  };

  // Fetch active punch state directly from PostgreSQL via FastAPI
  const fetchActiveStatus = useCallback(async () => {
    if (!user || !user.employee_id) return;
    try {
      const response = await fetch(`${API_BASE_URL}/api/punch/active/${user.employee_id}`);
      if (response.ok) {
        const data = await response.json();
        setIsClockedIn(data.is_clocked_in);

        if (data.is_clocked_in) {
          setElapsedSeconds(data.elapsed_seconds || 0);
        } else {
          setElapsedSeconds(0);
        }
      }
    } catch (error) {
      console.log('Error fetching active punch status:', error);
    } finally {
      setFetchingStatus(false);
    }
  }, [user, API_BASE_URL]);

  useEffect(() => {
    getCurrentLocation();
  }, []);

  useFocusEffect(
    useCallback(() => {
      fetchActiveStatus();
      const poller = setInterval(fetchActiveStatus, 3000);
      return () => clearInterval(poller);
    }, [fetchActiveStatus])
  );

  useEffect(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    if (isClockedIn) {
      timerRef.current = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    } else {
      setElapsedSeconds(0);
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [isClockedIn]);

  const formatTimer = (totalSecs) => {
    const hrs = Math.floor(totalSecs / 3600);
    const mins = Math.floor((totalSecs % 3600) / 60);
    const secs = totalSecs % 60;
    return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  const handlePunch = async () => {
    setLoading(true);
    const punchType = isClockedIn ? 'CLOCK_OUT' : 'CLOCK_IN';
    const locData = await getCurrentLocation();

    try {
      const response = await fetch(`${API_BASE_URL}/api/punch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          employee_id: user.employee_id,
          punch_type: punchType,
          latitude: locData.latitude,
          longitude: locData.longitude,
          accuracy: 10.0,
          address: locData.address,
        }),
      });

      if (response.ok) {
        await fetchActiveStatus();
      } else {
        Alert.alert('Punch Error', 'Failed to submit time punch to backend.');
      }
    } catch (error) {
      Alert.alert('Network Error', 'Unable to reach HRIS backend server.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      {/* Profile Header */}
      <View style={styles.headerCard}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{user?.name ? user.name.charAt(0) : 'U'}</Text>
        </View>
        <View style={styles.headerInfo}>
          <Text style={styles.userName}>{user?.name || 'Employee'}</Text>
          <Text style={styles.userDetails}>
            {user?.department || 'General'} • {user?.position || 'Staff'} ({user?.employee_id})
          </Text>
        </View>
        <TouchableOpacity onPress={logout} style={styles.logoutBtn}>
          <Ionicons name="log-out-outline" size={20} color="#64748b" />
        </TouchableOpacity>
      </View>

      {/* Main Clock Card */}
      <View style={styles.clockCard}>
        <View style={[styles.badge, isClockedIn ? styles.badgeOnDuty : styles.badgeOffDuty]}>
          <View style={[styles.dot, isClockedIn ? styles.dotOnDuty : styles.dotOffDuty]} />
          <Text style={[styles.badgeText, isClockedIn ? styles.badgeTextOnDuty : styles.badgeTextOffDuty]}>
            {isClockedIn ? 'ON DUTY' : 'OFF DUTY'}
          </Text>
        </View>

        <Text style={styles.timerText}>{formatTimer(elapsedSeconds)}</Text>
        <Text style={styles.subText}>
          {isClockedIn ? 'Shift duration running' : 'Ready to start shift'}
        </Text>

        <TouchableOpacity
          style={[styles.punchBtn, isClockedIn ? styles.punchBtnOut : styles.punchBtnIn]}
          onPress={handlePunch}
          disabled={loading || fetchingStatus}
          activeOpacity={0.85}
        >
          {loading ? (
            <ActivityIndicator color="#ffffff" />
          ) : (
            <Text style={styles.punchBtnText}>
              {isClockedIn ? 'CLOCK OUT NOW' : 'CLOCK IN NOW'}
            </Text>
          )}
        </TouchableOpacity>

        <Text style={styles.geoText}>{locationText}</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flexGrow: 1, backgroundColor: '#f8fafc', padding: 20, paddingTop: 40 },
  headerCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#ffffff', borderRadius: 16, padding: 16, marginBottom: 20, borderWidth: 1, borderColor: '#f1f5f9' },
  avatar: { width: 44, height: 44, borderRadius: 12, backgroundColor: '#2563eb', justifyContent: 'center', alignItems: 'center', marginRight: 12 },
  avatarText: { color: '#ffffff', fontWeight: '800', fontSize: 18 },
  headerInfo: { flex: 1 },
  userName: { fontSize: 16, fontWeight: '800', color: '#0f172a' },
  userDetails: { fontSize: 12, color: '#64748b', marginTop: 2 },
  logoutBtn: { padding: 8 },
  clockCard: { backgroundColor: '#ffffff', borderRadius: 20, padding: 28, alignItems: 'center', borderWidth: 1, borderColor: '#f1f5f9' },
  badge: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20, marginBottom: 16 },
  badgeOnDuty: { backgroundColor: '#dcfce7' },
  badgeOffDuty: { backgroundColor: '#f1f5f9' },
  dot: { width: 8, height: 8, borderRadius: 4, marginRight: 6 },
  dotOnDuty: { backgroundColor: '#16a34a' },
  dotOffDuty: { backgroundColor: '#64748b' },
  badgeText: { fontSize: 12, fontWeight: '800' },
  badgeTextOnDuty: { color: '#15803d' },
  badgeTextOffDuty: { color: '#475569' },
  timerText: { fontSize: 42, fontWeight: '800', color: '#0f172a', fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace', marginBottom: 4 },
  subText: { fontSize: 13, color: '#64748b', marginBottom: 24 },
  punchBtn: { width: '100%', height: 54, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  punchBtnIn: { backgroundColor: '#2563eb' },
  punchBtnOut: { backgroundColor: '#dc2626' },
  punchBtnText: { color: '#ffffff', fontWeight: '800', fontSize: 16 },
  geoText: { fontSize: 11, color: '#94a3b8', marginTop: 16, textAlign: 'center' },
});
