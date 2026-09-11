import React, { useState, useEffect, useContext, useCallback, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, Alert, ScrollView, Modal, TextInput, Platform } from 'react-native';
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

  const [showReviewModal, setShowReviewModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [gpsLoading, setGpsLoading] = useState(false);
  const [coords, setCoords] = useState(null);
  const [accuracy, setAccuracy] = useState(null);
  const [editReason, setEditReason] = useState('');

  const timerRef = useRef(null);

  const getHighAccuracyLocation = async () => {
    setGpsLoading(true);
    try {
      let { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission Required', 'GPS permission is needed.');
        setGpsLoading(false);
        return;
      }
      let loc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Highest, maximumAge: 0 });
      setCoords({ latitude: loc.coords.latitude, longitude: loc.coords.longitude });
      setAccuracy(Math.round(loc.coords.accuracy));
    } catch (error) {
      setCoords({ latitude: 14.5764, longitude: 121.0851 });
      setAccuracy(15);
    } finally {
      setGpsLoading(false);
    }
  };

  const fetchActiveStatus = useCallback(async () => {
    if (!user || !user.employee_id) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/punch/active/${user.employee_id}`);
      if (res.ok) {
        const data = await res.json();
        setIsClockedIn(data.is_clocked_in);
        setElapsedSeconds(data.is_clocked_in ? (data.elapsed_seconds || 0) : 0);
      }
    } catch (e) {
      console.log(e);
    } finally {
      setFetchingStatus(false);
    }
  }, [user, API_BASE_URL]);

  useFocusEffect(useCallback(() => {
    fetchActiveStatus();
    const poller = setInterval(fetchActiveStatus, 3000);
    return () => clearInterval(poller);
  }, [fetchActiveStatus]));

  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (isClockedIn) {
      timerRef.current = setInterval(() => setElapsedSeconds(p => p + 1), 1000);
    } else {
      setElapsedSeconds(0);
    }
    return () => clearInterval(timerRef.current);
  }, [isClockedIn]);

  const handleInitiatePunch = () => {
    setShowReviewModal(true);
    getHighAccuracyLocation();
  };

  const handleConfirmPunch = async () => {
    if (!coords) return Alert.alert('Wait', 'Acquiring GPS...');
    setLoading(true);
    setShowReviewModal(false);
    try {
      const res = await fetch(`${API_BASE_URL}/api/punch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          employee_id: user.employee_id,
          punch_type: isClockedIn ? 'CLOCK_OUT' : 'CLOCK_IN',
          latitude: coords.latitude,
          longitude: coords.longitude,
          accuracy: accuracy || 10.0,
          address: `GPS Pin: ${coords.latitude.toFixed(5)}, ${coords.longitude.toFixed(5)}`,
        }),
      });
      if (res.ok) await fetchActiveStatus();
    } catch (e) {
      Alert.alert('Error', 'Network error.');
    } finally {
      setLoading(false);
    }
  };

  const submitShiftEditRequest = async () => {
    if (!editReason) return Alert.alert('Error', 'Reason required.');
    setLoading(true);
    setShowEditModal(false);
    try {
      const res = await fetch(`${API_BASE_URL}/api/shift-request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          employee_id: user.employee_id,
          requested_punch_type: 'CLOCK_OUT',
          requested_timestamp: new Date().toISOString(),
          reason: editReason,
        }),
      });
      if (res.ok) {
        setEditReason('');
        Alert.alert('Success', 'Request sent to manager.');
      }
    } catch (e) {
      Alert.alert('Error', 'Network error.');
    } finally {
      setLoading(false);
    }
  };

  const formatTimer = (ts) => {
    const h = String(Math.floor(ts / 3600)).padStart(2, '0');
    const m = String(Math.floor((ts % 3600) / 60)).padStart(2, '0');
    const s = String(ts % 60).padStart(2, '0');
    return `${h}:${m}:${s}`;
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.headerCard}>
        <View style={styles.avatar}><Text style={styles.avatarText}>{user?.name?.charAt(0) || 'U'}</Text></View>
        <View style={styles.headerInfo}>
          <Text style={styles.userName}>{user?.name || 'Employee'}</Text>
          <Text style={styles.userDetails}>{user?.department} • {user?.position}</Text>
        </View>
        <TouchableOpacity onPress={logout} style={styles.logoutBtn}><Ionicons name="log-out-outline" size={20} color="#64748b" /></TouchableOpacity>
      </View>

      <View style={styles.clockCard}>
        <View style={[styles.badge, isClockedIn ? styles.badgeOnDuty : styles.badgeOffDuty]}>
          <View style={[styles.dot, isClockedIn ? styles.dotOnDuty : styles.dotOffDuty]} />
          <Text style={[styles.badgeText, isClockedIn ? styles.badgeTextOnDuty : styles.badgeTextOffDuty]}>{isClockedIn ? 'ON DUTY' : 'OFF DUTY'}</Text>
        </View>
        <Text style={styles.timerText}>{formatTimer(elapsedSeconds)}</Text>
        <TouchableOpacity style={[styles.punchBtn, isClockedIn ? styles.punchBtnOut : styles.punchBtnIn]} onPress={handleInitiatePunch} disabled={loading || fetchingStatus}>
          {loading ? <ActivityIndicator color="#ffffff" /> : <Text style={styles.punchBtnText}>{isClockedIn ? 'CLOCK OUT NOW' : 'CLOCK IN NOW'}</Text>}
        </TouchableOpacity>
      </View>

      {/* GPS REVIEW MODAL */}
      <Modal visible={showReviewModal} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Confirm DTR Location</Text>
            <Text style={styles.modalSub}>Action: <Text style={isClockedIn ? styles.textOut : styles.textIn}>{isClockedIn ? 'CLOCK OUT' : 'CLOCK IN'}</Text></Text>
            
            <View style={styles.gpsPreviewBox}>
              {gpsLoading ? <ActivityIndicator size="small" color="#2563eb" /> : (
                <View>
                  <Text style={styles.coordsTitle}>Current GPS</Text>
                  <Text style={styles.coordsVal}>{coords ? `Lat: ${coords.latitude.toFixed(5)}, Lng: ${coords.longitude.toFixed(5)}` : 'None'}</Text>
                  <Text style={styles.accuracyText}>Accuracy: ±{accuracy || 0}m</Text>
                </View>
              )}
            </View>
            
            <TouchableOpacity style={styles.recalibrateBtn} onPress={getHighAccuracyLocation} disabled={gpsLoading}>
              <Text style={styles.recalibrateText}>Recalibrate GPS</Text>
            </TouchableOpacity>

            <View style={styles.modalActions}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setShowReviewModal(false)}><Text style={styles.cancelBtnText}>Cancel</Text></TouchableOpacity>
              {isClockedIn && (
                <TouchableOpacity style={styles.editShiftBtn} onPress={() => { setShowReviewModal(false); setShowEditModal(true); }}>
                  <Text style={styles.editShiftBtnText}>Edit Shift</Text>
                </TouchableOpacity>
              )}
              <TouchableOpacity style={[styles.confirmBtn, isClockedIn ? styles.confirmBtnOut : styles.confirmBtnIn]} onPress={handleConfirmPunch} disabled={gpsLoading || !coords}>
                <Text style={styles.confirmBtnText}>Confirm</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* SHIFT EDIT MODAL */}
      <Modal visible={showEditModal} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Edit Shift Request</Text>
            <TextInput style={styles.reasonInput} placeholder="Reason (e.g., Forgot to clock in)" value={editReason} onChangeText={setEditReason} multiline />
            <View style={styles.modalActions}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setShowEditModal(false)}><Text style={styles.cancelBtnText}>Cancel</Text></TouchableOpacity>
              <TouchableOpacity style={styles.confirmBtnIn} onPress={submitShiftEditRequest}><Text style={styles.confirmBtnText}>Send Request</Text></TouchableOpacity>
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
  headerInfo: { flex: 1 }, userName: { fontSize: 16, fontWeight: '800', color: '#0f172a' }, userDetails: { fontSize: 12, color: '#64748b', marginTop: 2 },
  logoutBtn: { padding: 8 }, clockCard: { backgroundColor: '#ffffff', borderRadius: 20, padding: 28, alignItems: 'center', borderWidth: 1, borderColor: '#f1f5f9' },
  badge: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20, marginBottom: 16 },
  badgeOnDuty: { backgroundColor: '#dcfce7' }, badgeOffDuty: { backgroundColor: '#f1f5f9' }, dot: { width: 8, height: 8, borderRadius: 4, marginRight: 6 },
  dotOnDuty: { backgroundColor: '#16a34a' }, dotOffDuty: { backgroundColor: '#64748b' }, badgeText: { fontSize: 12, fontWeight: '800' },
  badgeTextOnDuty: { color: '#15803d' }, badgeTextOffDuty: { color: '#475569' },
  timerText: { fontSize: 42, fontWeight: '800', color: '#0f172a', fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace', marginBottom: 24 },
  punchBtn: { width: '100%', height: 54, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  punchBtnIn: { backgroundColor: '#2563eb' }, punchBtnOut: { backgroundColor: '#dc2626' }, punchBtnText: { color: '#ffffff', fontWeight: '800', fontSize: 16 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(15, 23, 42, 0.7)', justifyContent: 'center', padding: 20 },
  modalContent: { backgroundColor: '#ffffff', borderRadius: 24, padding: 22 },
  modalTitle: { fontSize: 18, fontWeight: '800', color: '#0f172a' }, modalSub: { fontSize: 12, color: '#64748b', marginBottom: 16 },
  textIn: { color: '#2563eb', fontWeight: '800' }, textOut: { color: '#dc2626', fontWeight: '800' },
  gpsPreviewBox: { backgroundColor: '#f8fafc', padding: 16, borderRadius: 16, borderWidth: 1, borderColor: '#e2e8f0', marginBottom: 12 },
  coordsTitle: { fontSize: 11, color: '#64748b', fontWeight: '700' }, coordsVal: { fontSize: 13, fontWeight: '700', color: '#0f172a' }, accuracyText: { fontSize: 10, color: '#16a34a', fontWeight: '700' },
  recalibrateBtn: { backgroundColor: '#eff6ff', paddingVertical: 10, borderRadius: 12, marginBottom: 20, alignItems: 'center' }, recalibrateText: { color: '#2563eb', fontWeight: '700', fontSize: 12 },
  modalActions: { flexDirection: 'row', gap: 8 }, editShiftBtn: { backgroundColor: '#fef08a', paddingHorizontal: 12, borderRadius: 12, justifyContent: 'center' }, editShiftBtnText: { color: '#854d0e', fontWeight: '700', fontSize: 13 },
  cancelBtn: { flex: 1, height: 48, borderRadius: 12, backgroundColor: '#f1f5f9', justifyContent: 'center', alignItems: 'center' }, cancelBtnText: { color: '#475569', fontWeight: '700', fontSize: 13 },
  confirmBtn: { flex: 1.5, height: 48, borderRadius: 12, justifyContent: 'center', alignItems: 'center' }, confirmBtnIn: { backgroundColor: '#2563eb', flex: 1.5, height: 48, borderRadius: 12, justifyContent: 'center', alignItems: 'center' }, confirmBtnOut: { backgroundColor: '#dc2626' }, confirmBtnText: { color: '#ffffff', fontWeight: '800', fontSize: 13 },
  reasonInput: { borderWidth: 1, borderColor: '#cbd5e1', borderRadius: 12, padding: 12, height: 80, textAlignVertical: 'top', fontSize: 13, marginBottom: 16 }
});
