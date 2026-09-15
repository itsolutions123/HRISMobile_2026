import React, { useState, useEffect, useContext, useCallback, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, Alert, ScrollView, Modal, Platform, TextInput, FlatList } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import * as Location from 'expo-location';
import { Ionicons } from '@expo/vector-icons';
import { AuthContext } from '../context/AuthContext';

export default function HomeScreen() {
  const { user, logout, API_BASE_URL } = useContext(AuthContext);
  const [isClockedIn, setIsClockedIn] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [activeJob, setActiveJob] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetchingStatus, setFetchingStatus] = useState(true);

  // Duty Selection States
  const [showDutyModal, setShowDutyModal] = useState(false);
  const [jobList, setJobList] = useState([]);
  const [searchDuty, setSearchDuty] = useState('');
  const [selectedDuty, setSelectedDuty] = useState(null);

  // GPS States
  const [showModal, setShowModal] = useState(false);
  const [gpsLoading, setGpsLoading] = useState(false);
  const [coords, setCoords] = useState(null);
  const [accuracy, setAccuracy] = useState(null);

  const timerRef = useRef(null);

  const fetchJobs = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/jobs`);
      if (res.ok) {
        const data = await res.json();
        let items = [];
        const userDept = (user?.department || '').trim().toLowerCase();
        const isAdmin = user?.role === 'Admin' || user?.role === 'SuperAdmin';

        data.forEach(cat => {
          const catNameLower = (cat.name || '').trim().toLowerCase();
          const catCodeLower = (cat.code || '').trim().toLowerCase();

          // Role-based Department Filtering:
          // Admins see all jobs; regular users only see jobs matching their department or code
          const isDeptMatch = isAdmin || !userDept || 
            catNameLower.includes(userDept) || 
            userDept.includes(catNameLower) ||
            catCodeLower.includes(userDept);

          if (isDeptMatch) {
            if (cat.sub_items && cat.sub_items.length > 0) {
              cat.sub_items.forEach(sub => {
                items.push({
                  id: `${cat.id}-${sub.id}`,
                  name: `${cat.name} - ${sub.name}`,
                  catName: cat.name,
                  subName: sub.name
                });
              });
            } else {
              items.push({
                id: `${cat.id}`,
                name: cat.name,
                catName: cat.name,
                subName: ''
              });
            }
          }
        });
        setJobList(items);
      }
    } catch (e) {
      console.log('Error fetching jobs:', e);
    }
  };

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
          setActiveJob(data.job_name || 'General Shift');
        } else {
          setElapsedSeconds(0);
          setActiveJob('');
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
      fetchJobs();
      fetchActiveStatus();
      const poller = setInterval(fetchActiveStatus, 3000);
      return () => clearInterval(poller);
    }, [fetchActiveStatus, user])
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

  const handleStartClockIn = () => {
    if (isClockedIn) {
      setSelectedDuty(null);
      setShowModal(true);
      getHighAccuracyLocation();
    } else {
      setShowDutyModal(true);
    }
  };

  const handleSelectDuty = (duty) => {
    setSelectedDuty(duty);
    setShowDutyModal(false);
    setShowModal(true);
    getHighAccuracyLocation();
  };

  const handleConfirmPunch = async () => {
    if (!coords) {
      Alert.alert('Location Missing', 'Please wait for GPS location or tap Recalibrate GPS.');
      return;
    }

    setLoading(true);
    setShowModal(false);
    const punchType = isClockedIn ? 'CLOCK_OUT' : 'CLOCK_IN';
    const dutyAddress = selectedDuty ? selectedDuty.name : activeJob || 'Duty Shift';

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
          address: dutyAddress,
        }),
      });

      if (response.ok) {
        await fetchActiveStatus();
      } else {
        const err = await response.json();
        Alert.alert('Punch Error', err.detail || 'Failed to save DTR punch record.');
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

  const filteredJobs = jobList.filter(j => j.name.toLowerCase().includes(searchDuty.toLowerCase()));

  return (
    <ScrollView contentContainerStyle={styles.container}>
      {/* Header Profile */}
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

      {/* Main Connecteam Card */}
      <View style={[styles.clockCard, isClockedIn && styles.clockCardActive]}>
        {isClockedIn && activeJob ? (
          <View style={styles.dutyPill}>
            <Text style={styles.dutyPillText}>Work time on • {activeJob}</Text>
          </View>
        ) : null}

        <Text style={styles.timerText}>{formatTimer(elapsedSeconds)}</Text>
        <Text style={styles.subText}>
          {isClockedIn ? `Clocked in on ${activeJob}` : 'Ready to start shift'}
        </Text>

        <View style={styles.actionRow}>
          {isClockedIn && (
            <TouchableOpacity
              style={styles.switchJobBtn}
              onPress={() => setShowDutyModal(true)}
            >
              <Ionicons name="swap-horizontal" size={18} color="#0284c7" />
              <Text style={styles.switchJobText}>Switch Job</Text>
            </TouchableOpacity>
          )}

          <TouchableOpacity
            style={[styles.punchBtn, isClockedIn ? styles.punchBtnOut : styles.punchBtnIn]}
            onPress={handleStartClockIn}
            disabled={loading || fetchingStatus}
            activeOpacity={0.85}
          >
            {loading ? (
              <ActivityIndicator color="#ffffff" />
            ) : (
              <Text style={styles.punchBtnText}>
                {isClockedIn ? 'End Shift' : 'Clock in'}
              </Text>
            )}
          </TouchableOpacity>
        </View>
      </View>

      {/* DUTY / JOB SELECTION MODAL */}
      <Modal visible={showDutyModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.dutyModalContent}>
            <View style={styles.modalHeader}>
              <View>
                <Text style={styles.modalTitle}>Select Duty / Position</Text>
                <Text style={styles.modalSub}>
                  Assigned Department: <Text style={{ fontWeight: '700', color: '#0284c7' }}>{user?.department || 'All'}</Text>
                </Text>
              </View>
              <TouchableOpacity onPress={() => setShowDutyModal(false)}>
                <Ionicons name="close" size={24} color="#64748b" />
              </TouchableOpacity>
            </View>

            <View style={styles.searchBox}>
              <Ionicons name="search" size={18} color="#94a3b8" />
              <TextInput
                style={styles.searchInput}
                placeholder="Search duty..."
                value={searchDuty}
                onChangeText={setSearchDuty}
              />
            </View>

            <FlatList
              data={filteredJobs}
              keyExtractor={(item) => item.id}
              renderItem={({ item }) => (
                <TouchableOpacity style={styles.dutyItem} onPress={() => handleSelectDuty(item)}>
                  <View style={styles.dutyDot} />
                  <Text style={styles.dutyItemText}>{item.name}</Text>
                </TouchableOpacity>
              )}
              ListEmptyComponent={<Text style={styles.emptyText}>No matching duties for {user?.department || 'your department'}.</Text>}
              style={{ maxHeight: 300 }}
            />
          </View>
        </View>
      </Modal>

      {/* PRE-PUNCH LOCATION CONFIRMATION MODAL */}
      <Modal visible={showModal} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <View>
                <Text style={styles.modalTitle}>Confirm GPS Location</Text>
                <Text style={styles.modalSub}>
                  Duty: <Text style={{ fontWeight: 'bold', color: '#0284c7' }}>{selectedDuty ? selectedDuty.name : activeJob || 'Shift'}</Text>
                </Text>
              </View>
              <TouchableOpacity onPress={() => setShowModal(false)}>
                <Ionicons name="close" size={24} color="#64748b" />
              </TouchableOpacity>
            </View>

            <View style={styles.gpsPreviewBox}>
              <Ionicons name="navigate-circle" size={36} color="#0284c7" />
              {gpsLoading ? (
                <View style={{ flex: 1, marginLeft: 10 }}>
                  <ActivityIndicator size="small" color="#0284c7" />
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

            <TouchableOpacity style={styles.recalibrateBtn} onPress={getHighAccuracyLocation} disabled={gpsLoading}>
              <Ionicons name="refresh" size={16} color="#0284c7" />
              <Text style={styles.recalibrateText}>Recalibrate GPS Location</Text>
            </TouchableOpacity>

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
                  {isClockedIn ? 'Confirm End Shift' : 'Confirm Clock In'}
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
  headerCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#ffffff', borderRadius: 16, padding: 16, marginBottom: 20, borderWidth: 1, borderColor: '#e2e8f0' },
  avatar: { width: 44, height: 44, borderRadius: 12, backgroundColor: '#0284c7', justifyContent: 'center', alignItems: 'center', marginRight: 12 },
  avatarText: { color: '#ffffff', fontWeight: '800', fontSize: 18 },
  headerInfo: { flex: 1 },
  userName: { fontSize: 16, fontWeight: '800', color: '#0f172a' },
  userDetails: { fontSize: 12, color: '#64748b', marginTop: 2 },
  logoutBtn: { padding: 8 },
  clockCard: { backgroundColor: '#ffffff', borderRadius: 20, padding: 24, alignItems: 'center', borderWidth: 1, borderColor: '#e2e8f0' },
  clockCardActive: { backgroundColor: '#0284c7', borderColor: '#0284c7' },
  dutyPill: { backgroundColor: 'rgba(255,255,255,0.2)', paddingHorizontal: 14, paddingVertical: 6, borderRadius: 20, marginBottom: 12 },
  dutyPillText: { color: '#ffffff', fontWeight: '700', fontSize: 13 },
  timerText: { fontSize: 42, fontWeight: '800', color: '#0f172a', marginBottom: 4 },
  subText: { fontSize: 13, color: '#64748b', marginBottom: 20 },
  actionRow: { flexDirection: 'row', gap: 10, width: '100%' },
  switchJobBtn: { flex: 1, backgroundColor: '#ffffff', height: 48, borderRadius: 12, flexDirection: 'row', justifyContent: 'center', alignItems: 'center', gap: 6 },
  switchJobText: { color: '#0284c7', fontWeight: '700', fontSize: 14 },
  punchBtn: { flex: 1, height: 48, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  punchBtnIn: { backgroundColor: '#0284c7' },
  punchBtnOut: { backgroundColor: '#ef4444' },
  punchBtnText: { color: '#ffffff', fontWeight: '800', fontSize: 15 },

  modalOverlay: { flex: 1, backgroundColor: 'rgba(15, 23, 42, 0.7)', justifyContent: 'center', padding: 20 },
  dutyModalContent: { backgroundColor: '#ffffff', borderRadius: 24, padding: 20 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  modalTitle: { fontSize: 18, fontWeight: '800', color: '#0f172a' },
  modalSub: { fontSize: 12, color: '#64748b', marginTop: 2 },
  searchBox: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#f1f5f9', paddingHorizontal: 12, borderRadius: 10, marginBottom: 12 },
  searchInput: { flex: 1, paddingVertical: 10, marginLeft: 8, fontSize: 14 },
  dutyItem: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#f1f5f9' },
  dutyDot: { width: 12, height: 12, borderRadius: 6, backgroundColor: '#0284c7', marginRight: 12 },
  dutyItemText: { fontSize: 14, fontWeight: '600', color: '#1e293b' },
  emptyText: { textAlign: 'center', color: '#94a3b8', marginVertical: 20 },

  modalContent: { backgroundColor: '#ffffff', borderRadius: 24, padding: 22 },
  gpsPreviewBox: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#f8fafc', padding: 16, borderRadius: 16, borderWidth: 1, borderColor: '#e2e8f0', marginBottom: 12 },
  gpsLoadingText: { fontSize: 12, color: '#64748b', marginTop: 4 },
  coordsTitle: { fontSize: 11, color: '#64748b', fontWeight: '700', textTransform: 'uppercase' },
  coordsVal: { fontSize: 13, fontWeight: '700', color: '#0f172a' },
  accuracyText: { fontSize: 10, color: '#16a34a', fontWeight: '700', marginTop: 2 },
  recalibrateBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: '#eff6ff', paddingVertical: 10, borderRadius: 12, marginBottom: 20, justifyContent: 'center' },
  recalibrateText: { color: '#0284c7', fontWeight: '700', fontSize: 12 },
  modalActions: { flexDirection: 'row', gap: 10 },
  cancelBtn: { flex: 1, height: 48, borderRadius: 12, backgroundColor: '#f1f5f9', justifyContent: 'center', alignItems: 'center' },
  cancelBtnText: { color: '#475569', fontWeight: '700', fontSize: 14 },
  confirmBtn: { flex: 1.5, height: 48, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  confirmBtnIn: { backgroundColor: '#0284c7' },
  confirmBtnOut: { backgroundColor: '#ef4444' },
  confirmBtnText: { color: '#ffffff', fontWeight: '800', fontSize: 14 },
});
