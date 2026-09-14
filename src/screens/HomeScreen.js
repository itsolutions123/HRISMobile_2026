import React, { useState, useEffect, useContext, useCallback, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, Alert, ScrollView, Modal, Platform } from 'react-native';
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

  // Modal and GPS States
  const [showModal, setShowModal] = useState(false);
  const [gpsLoading, setGpsLoading] = useState(false);
  const [coords, setCoords] = useState(null);
  const [accuracy, setAccuracy] = useState(null);

  const timerRef = useRef(null);

  // Acquire High-Precision Device Hardware GPS
  const getHighAccuracyLocation = async () => {
    setGpsLoading(true);
    try {
      let { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission Required', 'GPS permission is needed to record DTR attendance.');
        setGpsLoading(false);
        return false;
      }

      let location = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Highest,
        maximumAge: 0,
      });

      setCoords({
        latitude: location.coords.latitude,
        longitude: location.coords.longitude,
      });
      setAccuracy(Math.round(location.coords.accuracy));
      return true;
    } catch (error) {
      console.log('GPS Error:', error);
      Alert.alert('GPS Fix Error', 'Unable to acquire satellite fix. Tap Recalibrate GPS to retry.');
      return false;
    } finally {
      setGpsLoading(false);
    }
  };

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
      console.log('Error fetching active status:', error);
    } finally {
      setFetchingStatus(false);
    }
  }, [user, API_BASE_URL]);

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
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isClockedIn]);

  // Open modal directly on UI thread first, then query hardware GPS
  const handleInitiatePunch = () => {
    setShowModal(true);
    getHighAccuracyLocation();
  };

  // Submit Final DTR Punch to Backend
  const handleConfirmPunch = async () => {
    if (!coords) {
      Alert.alert('Location Missing', 'Please wait for GPS location or tap Recalibrate GPS.');
      return;
    }

    setLoading(true);
    setShowModal(false);
    const punchType = isClockedIn ? 'CLOCK_OUT' : 'CLOCK_IN';

    try {
      const response = await fetch(`${API_BASE_URL}/api/punch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          employee_id: user.employee_id,
          punch_type: punchType,
          latitude: coords.latitude,
          longitude: coords.longitude,
          accuracy: accuracy || 10.0,
          address: `GPS Pin: ${coords.latitude.toFixed(5)}, ${coords.longitude.toFixed(5)}`,
        }),
      });

      if (response.ok) {
        await fetchActiveStatus();
      } else {
        Alert.alert('Punch Error', 'Failed to save DTR punch record.');
      }
    } catch (error) {
      Alert.alert('Network Error', 'Unable to reach backend server.');
    } finally {
      setLoading(false);
    }
  };

  const formatTimer = (totalSecs) => {
    const hrs = Math.floor(totalSecs / 3600);
    const mins = Math.floor((totalSecs % 3600) / 60);
    const secs = totalSecs % 60;
    return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
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
          onPress={handleInitiatePunch}
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
      </View>

      {/* PRE-PUNCH LOCATION REVIEW POP-UP MODAL */}
      <Modal visible={showModal} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            
            <View style={styles.modalHeader}>
              <View>
                <Text style={styles.modalTitle}>Confirm DTR Location</Text>
                <Text style={styles.modalSub}>
                  Action: <Text style={isClockedIn ? styles.textOut : styles.textIn}>{isClockedIn ? 'CLOCK OUT' : 'CLOCK IN'}</Text>
                </Text>
              </View>
              <TouchableOpacity onPress={() => setShowModal(false)}>
                <Ionicons name="close" size={24} color="#64748b" />
              </TouchableOpacity>
            </View>

            {/* GPS Preview Box */}
            <View style={styles.gpsPreviewBox}>
              <Ionicons name="navigate-circle" size={36} color="#2563eb" />
              {gpsLoading ? (
                <View style={{ flex: 1, marginLeft: 10 }}>
                  <ActivityIndicator size="small" color="#2563eb" />
                  <Text style={styles.gpsLoadingText}>Acquiring high-accuracy GPS fix...</Text>
                </View>
              ) : coords ? (
                <View style={{ flex: 1, marginLeft: 10 }}>
                  <Text style={styles.coordsTitle}>Current GPS Location</Text>
                  <Text style={styles.coordsVal}>Lat: {coords.latitude.toFixed(5)}</Text>
                  <Text style={styles.coordsVal}>Lng: {coords.longitude.toFixed(5)}</Text>
                  <Text style={styles.accuracyText}>Satellite Accuracy: ±{accuracy || 10} meters</Text>
                </View>
              ) : (
                <Text style={styles.gpsErrorText}>Location not acquired</Text>
              )}
            </View>

            {/* Recalibrate Button */}
            <TouchableOpacity 
              style={styles.recalibrateBtn} 
              onPress={getHighAccuracyLocation}
              disabled={gpsLoading}
            >
              <Ionicons name="refresh" size={16} color="#2563eb" />
              <Text style={styles.recalibrateText}>Recalibrate GPS Location</Text>
            </TouchableOpacity>

            {/* Action Buttons */}
            <View style={styles.modalActions}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setShowModal(false)}>
                <Text style={styles.cancelBtnText}>Cancel</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.confirmBtn, isClockedIn ? styles.confirmBtnOut : styles.confirmBtnIn]}
                onPress={handleConfirmPunch}
                disabled={gpsLoading || !coords}
              >
                <Text style={styles.confirmBtnText}>
                  {isClockedIn ? 'Confirm Time Out' : 'Confirm Time In'}
                </Text>
              </TouchableOpacity>
            </View>

          </View>
        </View>
      </Modal>

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

  // Modal Styles
  modalOverlay: { flex: 1, backgroundColor: 'rgba(15, 23, 42, 0.7)', justifyContent: 'center', padding: 20 },
  modalContent: { backgroundColor: '#ffffff', borderRadius: 24, padding: 22, borderWidth: 1, borderColor: '#f1f5f9' },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  modalTitle: { fontSize: 18, fontWeight: '800', color: '#0f172a' },
  modalSub: { fontSize: 12, color: '#64748b', marginTop: 2 },
  textIn: { color: '#2563eb', fontWeight: '800' },
  textOut: { color: '#dc2626', fontWeight: '800' },
  gpsPreviewBox: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#f8fafc', padding: 16, borderRadius: 16, borderWidth: 1, borderColor: '#e2e8f0', marginBottom: 12 },
  gpsLoadingText: { fontSize: 12, color: '#64748b', marginTop: 4 },
  coordsTitle: { fontSize: 11, color: '#64748b', fontWeight: '700', textTransform: 'uppercase' },
  coordsVal: { fontSize: 13, fontWeight: '700', color: '#0f172a', fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace' },
  accuracyText: { fontSize: 10, color: '#16a34a', fontWeight: '700', marginTop: 2 },
  recalibrateBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: '#eff6ff', paddingVertical: 10, borderRadius: 12, marginBottom: 20, justifyContent: 'center' },
  recalibrateText: { color: '#2563eb', fontWeight: '700', fontSize: 12 },
  modalActions: { flexDirection: 'row', gap: 10 },
  cancelBtn: { flex: 1, height: 48, borderRadius: 12, backgroundColor: '#f1f5f9', justifyContent: 'center', alignItems: 'center' },
  cancelBtnText: { color: '#475569', fontWeight: '700', fontSize: 14 },
  confirmBtn: { flex: 1.5, height: 48, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  confirmBtnIn: { backgroundColor: '#2563eb' },
  confirmBtnOut: { backgroundColor: '#dc2626' },
  confirmBtnText: { color: '#ffffff', fontWeight: '800', fontSize: 14 },
});
