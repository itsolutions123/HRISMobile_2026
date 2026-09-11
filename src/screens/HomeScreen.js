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

  // Review & Edit Modals
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [capturedLoc, setCapturedLoc] = useState(null);

  // Shift Edit Request form states
  const [editReason, setReason] = useState('');

  const timerRef = useRef(null);

  const getCurrentLocation = async () => {
    try {
      let { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        return { latitude: 14.5764, longitude: 121.0851, address: 'Pasig, Metro Manila (Permission Denied)' };
      }
      let loc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High });
      return {
        latitude: loc.coords.latitude,
        longitude: loc.coords.longitude,
        address: `GPS Pin: ${loc.coords.latitude.toFixed(4)}, ${loc.coords.longitude.toFixed(4)}`
      };
    } catch (e) {
      return { latitude: 14.5764, longitude: 121.0851, address: 'Pasig, Metro Manila' };
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
      console.log('Active punch fetch error:', error);
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
      timerRef.current = setInterval(() => setElapsedSeconds((prev) => prev + 1), 1000);
    } else {
      setElapsedSeconds(0);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isClockedIn]);

  const initiatePunchReview = async () => {
    setLoading(true);
    const loc = await getCurrentLocation();
    setCapturedLoc(loc);
    setLoading(false);
    setShowReviewModal(true);
  };

  const confirmPunch = async () => {
    setShowReviewModal(false);
    setLoading(true);
    const punchType = isClockedIn ? 'CLOCK_OUT' : 'CLOCK_IN';

    try {
      const response = await fetch(`${API_BASE_URL}/api/punch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          employee_id: user.employee_id,
          punch_type: punchType,
          latitude: capturedLoc ? capturedLoc.latitude : 14.5764,
          longitude: capturedLoc ? capturedLoc.longitude : 121.0851,
          accuracy: 10.0,
          address: capturedLoc ? capturedLoc.address : 'Pasig, Metro Manila',
        }),
      });

      if (response.ok) {
        await fetchActiveStatus();
      } else {
        Alert.alert('Punch Error', 'Failed to submit time punch to backend.');
      }
    } catch (error) {
      Alert.alert('Network Error', 'Unable to reach backend.');
    } finally {
      setLoading(false);
    }
  };

  const submitShiftEditRequest = async () => {
    if (!editReason) {
      Alert.alert('Missing Reason', 'Please provide a reason for manager approval.');
      return;
    }

    setLoading(true);
    const punchType = isClockedIn ? 'CLOCK_OUT' : 'CLOCK_IN';
    const nowIso = new Date().toISOString();

    try {
      const response = await fetch(`${API_BASE_URL}/api/shift-request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          employee_id: user.employee_id,
          requested_punch_type: punchType,
          requested_timestamp: nowIso,
          reason: editReason,
        }),
      });

      if (response.ok) {
        setShowEditModal(false);
        setReason('');
        Alert.alert('Request Sent', 'Your shift edit request has been submitted to your supervisor for approval.');
      } else {
        Alert.alert('Submission Error', 'Failed to submit shift edit request.');
      }
    } catch (e) {
      Alert.alert('Network Error', 'Unable to reach backend.');
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
          onPress={initiatePunchReview}
          disabled={loading}
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

      {/* PRE-PUNCH LOCATION REVIEW MODAL */}
      <Modal visible={showReviewModal} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Review DTR Punch Location</Text>
            <Text style={styles.modalSub}>
              Action: <Text style={{ fontWeight: 'bold' }}>{isClockedIn ? 'CLOCK_OUT' : 'CLOCK_IN'}</Text>
            </Text>

            <View style={styles.locBox}>
              <Ionicons name="location" size={20} color="#2563eb" />
              <Text style={styles.locText}>{capturedLoc?.address || 'Captured GPS Coordinates'}</Text>
            </View>

            <View style={styles.modalBtnGroup}>
              <TouchableOpacity
                style={styles.editShiftBtn}
                onPress={() => {
                  setShowReviewModal(false);
                  setShowEditModal(true);
                }}
              >
                <Text style={styles.editShiftBtnText}>Edit Shift</Text>
              </TouchableOpacity>

              <TouchableOpacity style={styles.confirmBtn} onPress={confirmPunch}>
                <Text style={styles.confirmBtnText}>Confirm Punch</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* SHIFT EDIT APPROVAL MODAL */}
      <Modal visible={showEditModal} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Edit Shift Request</Text>
            <Text style={styles.modalSub}>Submit a manual correction for Manager Approval</Text>

            <TextInput
              style={styles.reasonInput}
              placeholder="Reason for edit (e.g., Forgot to clock in, field assignment)"
              value={editReason}
              onChangeText={setReason}
              multiline
            />

            <View style={styles.modalBtnGroup}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setShowEditModal(false)}>
                <Text style={styles.cancelBtnText}>Cancel</Text>
              </TouchableOpacity>

              <TouchableOpacity style={styles.confirmBtn} onPress={submitShiftEditRequest}>
                <Text style={styles.confirmBtnText}>Send Request</Text>
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
  
  // Modals
  modalOverlay: { flex: 1, backgroundColor: 'rgba(15, 23, 42, 0.6)', justifyContent: 'center', alignItems: 'center', padding: 20 },
  modalContent: { width: '100%', backgroundColor: '#ffffff', borderRadius: 20, padding: 24, spaceY: 16 },
  modalTitle: { fontSize: 18, fontWeight: '800', color: '#0f172a', marginBottom: 4 },
  modalSub: { fontSize: 13, color: '#64748b', marginBottom: 16 },
  locBox: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#f8fafc', padding: 12, borderRadius: 12, borderWidth: 1, borderColor: '#e2e8f0', marginBottom: 20 },
  locText: { marginLeft: 8, fontSize: 12, color: '#334155', flex: 1 },
  modalBtnGroup: { flexDirection: 'row', gap: 10, justifyContent: 'flex-end' },
  editShiftBtn: { backgroundColor: '#f1f5f9', paddingVertical: 12, paddingHorizontal: 16, borderRadius: 10 },
  editShiftBtnText: { color: '#334155', fontWeight: '700', fontSize: 13 },
  confirmBtn: { backgroundColor: '#16a34a', paddingVertical: 12, paddingHorizontal: 16, borderRadius: 10 },
  confirmBtnText: { color: '#ffffff', fontWeight: '700', fontSize: 13 },
  cancelBtn: { backgroundColor: '#f1f5f9', paddingVertical: 12, paddingHorizontal: 16, borderRadius: 10 },
  cancelBtnText: { color: '#64748b', fontWeight: '700', fontSize: 13 },
  reasonInput: { borderWidth: 1, borderColor: '#cbd5e1', borderRadius: 10, padding: 12, height: 80, textAlignVertical: 'top', fontSize: 13, marginBottom: 20 }
});
