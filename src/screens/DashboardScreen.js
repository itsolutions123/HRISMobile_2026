import React, { useState, useEffect, useContext, useCallback, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, Alert, Modal, ScrollView } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import * as Location from 'expo-location';
import { WebView } from 'react-native-webview';
import { Ionicons } from '@expo/vector-icons';
import { AuthContext } from '../context/AuthContext';

const JOB_LIST = ['IT Assistant', 'System Administrator', 'IT Head', 'Technical Support Specialist'];

export default function DashboardScreen() {
  const { user, logout, API_BASE_URL } = useContext(AuthContext);
  const [isClockedIn, setIsClockedIn] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [loading, setLoading] = useState(false);
  const [gpsLoading, setGpsLoading] = useState(false);
  
  const [location, setLocation] = useState({
    latitude: 14.5764,
    longitude: 121.0851,
  });
  const [showJobModal, setShowJobModal] = useState(false);
  const [selectedJob, setSelectedJob] = useState('System Administrator');
  
  const timerRef = useRef(null);

  const requestGpsLocation = async () => {
    setGpsLoading(true);
    try {
      let { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        setGpsLoading(false);
        return;
      }

      // 1. Fast fallback: grab last known position immediately
      let lastLoc = await Location.getLastKnownPositionAsync({});
      if (lastLoc && lastLoc.coords) {
        setLocation({
          latitude: lastLoc.coords.latitude,
          longitude: lastLoc.coords.longitude,
        });
      }

      // 2. Fetch fresh high-accuracy position with 4-second timeout
      const locPromise = Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
      const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error('GPS Timeout')), 4000));

      const freshLoc = await Promise.race([locPromise, timeoutPromise]);
      if (freshLoc && freshLoc.coords) {
        setLocation({
          latitude: freshLoc.coords.latitude,
          longitude: freshLoc.coords.longitude,
        });
      }
    } catch (e) {
      // Keep last known or fallback location
    }
    setGpsLoading(false);
  };

  const fetchStatus = useCallback(async () => {
    if (!user || !user.employee_id) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/punch/active/${user.employee_id}`);
      if (res.ok) {
        const data = await res.json();
        setIsClockedIn(data.is_clocked_in);
        setElapsedSeconds(data.is_clocked_in ? (data.elapsed_seconds || 0) : 0);
      }
    } catch (e) {}
  }, [user, API_BASE_URL]);

  useFocusEffect(useCallback(() => {
    requestGpsLocation();
    fetchStatus();
    const poller = setInterval(fetchStatus, 4000);
    return () => clearInterval(poller);
  }, [fetchStatus]));

  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (isClockedIn) timerRef.current = setInterval(() => setElapsedSeconds(p => p + 1), 1000);
    return () => clearInterval(timerRef.current);
  }, [isClockedIn]);

  const submitPunch = async (jobName = selectedJob) => {
    setLoading(true);
    setShowJobModal(false);
    try {
      const res = await fetch(`${API_BASE_URL}/api/punch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          employee_id: user.employee_id,
          punch_type: isClockedIn ? 'CLOCK_OUT' : 'CLOCK_IN',
          latitude: location ? location.latitude : 14.5764,
          longitude: location ? location.longitude : 121.0851,
          accuracy: 10,
          address: isClockedIn ? 'Shift Ended' : `Job: ${jobName}`,
        }),
      });
      if (res.ok) await fetchStatus();
    } catch (e) {
      Alert.alert('Error', 'Failed to connect to backend server.');
    }
    setLoading(false);
  };

  const formatTime = (ts) => {
    const h = String(Math.floor(ts / 3600)).padStart(2, '0');
    const m = String(Math.floor((ts % 3600) / 60)).padStart(2, '0');
    const s = String(ts % 60).padStart(2, '0');
    return `${h}:${m}:${s}`;
  };

  const leafletHtml = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
      <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
      <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
      <style>
        body, html, #map { height: 100%; width: 100%; margin: 0; padding: 0; background-color: #e2e8f0; }
      </style>
    </head>
    <body>
      <div id="map"></div>
      <script>
        var map = L.map('map', { zoomControl: false, attributionControl: false }).setView([${location.latitude}, ${location.longitude}], 16);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map);
        L.marker([${location.latitude}, ${location.longitude}]).addTo(map);
      </script>
    </body>
    </html>
  `;

  if (isClockedIn) {
    return (
      <View style={styles.activeShiftContainer}>
        <View style={styles.topBar}>
          <TouchableOpacity onPress={logout}><Ionicons name="arrow-back" size={24} color="#000" /></TouchableOpacity>
          <Text style={styles.topBarTitle}>Head Office</Text>
          <Ionicons name="calendar-outline" size={24} color="#eab308" />
        </View>

        <View style={styles.activeCard}>
          <View style={styles.jobPill}>
            <Text style={styles.jobPillText}>HO IT - {selectedJob}</Text>
          </View>
          <Text style={styles.activeTimer}>{formatTime(elapsedSeconds)}</Text>
          <View style={styles.locRow}>
            <Ionicons name="location" size={14} color="#fff" />
            <Text style={styles.locText}>Clocked in at: GPS Pin {location?.latitude.toFixed(4)}</Text>
          </View>
          <View style={styles.cardFooter}>
            <Text style={styles.footerText}>Total work hours today</Text>
            <Text style={styles.footerText}>{formatTime(elapsedSeconds)}</Text>
          </View>
        </View>

        <View style={styles.tabRow}>
          <Text style={styles.activeTab}>Attachments</Text>
          <Text style={styles.inactiveTab}>My day log</Text>
        </View>

        <ScrollView style={styles.detailsList}>
          <Text style={styles.detailsTitle}>Details to Add (3)</Text>
          {['Time In', 'OB Form', 'Add a note'].map((item, i) => (
            <View key={i} style={styles.detailItem}>
              <View style={{flexDirection: 'row', alignItems: 'center', gap: 8}}>
                <Ionicons name="create-outline" size={18} color="#64748b" />
                <Text style={styles.detailText}>{item}</Text>
              </View>
              <TouchableOpacity style={styles.uploadBtn}><Text style={styles.uploadText}>{item === 'OB Form' ? 'Add a file' : 'Upload'}</Text></TouchableOpacity>
            </View>
          ))}
        </ScrollView>

        <View style={styles.bottomActions}>
          <TouchableOpacity style={styles.switchJobBtn}><Text style={styles.switchJobText}>Switch Job</Text></TouchableOpacity>
          <TouchableOpacity style={styles.endShiftBtn} onPress={() => submitPunch()} disabled={loading}>
            {loading ? <ActivityIndicator color="#fff"/> : <Text style={styles.endShiftText}>End Shift</Text>}
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.headerAbsolute}>
        <View style={styles.headerInfo}>
          <View style={styles.avatar}><Text style={{color:'#fff'}}>{user?.name?.charAt(0) || 'U'}</Text></View>
          <View>
            <Text style={styles.greeting}>Good day, {user?.name}</Text>
            <Text style={styles.subGreeting}>{user?.position} • {user?.department}</Text>
          </View>
        </View>
        <TouchableOpacity onPress={requestGpsLocation} style={styles.recenterBtn}>
          {gpsLoading ? <ActivityIndicator size="small" color="#2563eb" /> : <Ionicons name="locate" size={22} color="#2563eb" />}
        </TouchableOpacity>
      </View>

      <WebView
        key={`${location.latitude}-${location.longitude}`}
        style={styles.mapFullscreen}
        originWhitelist={['*']}
        source={{ html: leafletHtml }}
        scrollEnabled={false}
      />

      <View style={styles.bottomDrawer}>
        <View style={styles.clockBtnWrapper}>
          <TouchableOpacity style={styles.bigClockBtn} onPress={() => setShowJobModal(true)}>
            <Ionicons name="stopwatch-outline" size={36} color="#ffffff" />
            <Text style={styles.bigClockText}>Clock in</Text>
          </TouchableOpacity>
        </View>
        
        <View style={styles.drawerActions}>
          <TouchableOpacity style={styles.drawerActionBtn}>
            <Ionicons name="checkmark-circle-outline" size={24} color="#f59e0b" />
            <Text style={styles.actionText}>My requests</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.drawerActionBtn}>
            <Ionicons name="calendar-outline" size={24} color="#3b82f6" />
            <Text style={styles.actionText}>Timesheet</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* JOB SELECTION MODAL */}
      <Modal visible={showJobModal} transparent animationType="slide">
        <View style={styles.modalBg}>
          <View style={styles.modalSheet}>
            <View style={styles.modalHeader}>
              <TouchableOpacity onPress={() => setShowJobModal(false)}><Ionicons name="arrow-back" size={24} color="#000" /></TouchableOpacity>
              <Text style={styles.modalTitle}>HO IT</Text>
              <View style={{width: 24}}/>
            </View>
            
            <View style={styles.searchBar}>
              <Text style={{color:'#94a3b8'}}>Search</Text>
              <Ionicons name="search" size={18} color="#94a3b8" />
            </View>

            <ScrollView style={{width: '100%'}}>
              {JOB_LIST.map((job, idx) => (
                <TouchableOpacity key={idx} style={styles.jobRow} onPress={() => { setSelectedJob(job); submitPunch(job); }}>
                  <View style={styles.jobDot}/>
                  <Text style={styles.jobText}>{job}</Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
            
            <TouchableOpacity style={styles.cancelModalBtn} onPress={() => setShowJobModal(false)}>
              <Text style={styles.cancelModalText}>Cancel</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f1f5f9' },
  headerAbsolute: { position: 'absolute', top: 40, left: 20, right: 20, zIndex: 10, flexDirection: 'row', justifyContent: 'space-between', backgroundColor: 'rgba(255,255,255,0.95)', padding: 12, borderRadius: 16, alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.1, shadowRadius: 6, elevation: 5 },
  headerInfo: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  avatar: { width: 40, height: 40, borderRadius: 20, backgroundColor: '#1e3a8a', alignItems: 'center', justifyContent: 'center' },
  greeting: { fontWeight: '700', fontSize: 15, color: '#0f172a' },
  subGreeting: { fontSize: 11, color: '#64748b' },
  recenterBtn: { padding: 6, borderRadius: 12, backgroundColor: '#eff6ff' },
  mapFullscreen: { flex: 1, width: '100%' },
  bottomDrawer: { position: 'absolute', bottom: 0, width: '100%', backgroundColor: '#ffffff', borderTopLeftRadius: 30, borderTopRightRadius: 30, paddingBottom: 30, paddingTop: 60, alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.1, shadowRadius: 10, elevation: 10 },
  clockBtnWrapper: { position: 'absolute', top: -70, alignSelf: 'center', backgroundColor: '#f1f5f9', borderRadius: 80, padding: 10 },
  bigClockBtn: { width: 140, height: 140, borderRadius: 70, backgroundColor: '#3b82f6', alignItems: 'center', justifyContent: 'center', shadowColor: '#3b82f6', shadowOpacity: 0.4, shadowRadius: 10, elevation: 8 },
  bigClockText: { color: '#ffffff', fontWeight: '700', fontSize: 18, marginTop: 4 },
  drawerActions: { flexDirection: 'row', width: '100%', justifyContent: 'space-around', marginTop: 20 },
  drawerActionBtn: { alignItems: 'center', gap: 6 },
  actionText: { fontSize: 12, color: '#334155' },
  
  // Shift Active View
  activeShiftContainer: { flex: 1, backgroundColor: '#ffffff', paddingTop: 50 },
  topBar: { flexDirection: 'row', justifyContent: 'space-between', paddingHorizontal: 20, marginBottom: 20, alignItems: 'center' },
  topBarTitle: { fontSize: 16, fontWeight: '700' },
  activeCard: { backgroundColor: '#0ea5e9', marginHorizontal: 20, borderRadius: 20, padding: 20, alignItems: 'center' },
  jobPill: { backgroundColor: 'rgba(255,255,255,0.2)', paddingHorizontal: 16, paddingVertical: 4, borderRadius: 20, marginBottom: 12 },
  jobPillText: { color: '#fff', fontSize: 12, fontWeight: '600' },
  activeTimer: { fontSize: 48, fontWeight: '800', color: '#fff', marginBottom: 12 },
  locRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 20 },
  locText: { color: '#e0f2fe', fontSize: 12 },
  cardFooter: { flexDirection: 'row', justifyContent: 'space-between', width: '100%', borderTopWidth: 1, borderColor: 'rgba(255,255,255,0.2)', paddingTop: 12 },
  footerText: { color: '#fff', fontSize: 12, fontWeight: '600' },
  tabRow: { flexDirection: 'row', paddingHorizontal: 20, marginTop: 20, borderBottomWidth: 1, borderColor: '#e2e8f0' },
  activeTab: { fontWeight: '700', borderBottomWidth: 2, borderColor: '#0ea5e9', paddingBottom: 10, marginRight: 20 },
  inactiveTab: { color: '#64748b', paddingBottom: 10 },
  detailsList: { flex: 1, padding: 20 },
  detailsTitle: { fontSize: 16, fontWeight: '700', marginBottom: 16 },
  detailItem: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 14, borderBottomWidth: 1, borderColor: '#f1f5f9' },
  detailText: { fontSize: 14, color: '#334155' },
  uploadBtn: { borderWidth: 1, borderColor: '#cbd5e1', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 16 },
  uploadText: { fontSize: 12, color: '#64748b' },
  bottomActions: { flexDirection: 'row', padding: 20, gap: 12, borderTopWidth: 1, borderColor: '#f1f5f9' },
  switchJobBtn: { flex: 1, backgroundColor: '#f1f5f9', height: 48, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  switchJobText: { color: '#3b82f6', fontWeight: '700' },
  endShiftBtn: { flex: 1.5, backgroundColor: '#ef4444', height: 48, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  endShiftText: { color: '#fff', fontWeight: '700' },

  // Modal
  modalBg: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modalSheet: { backgroundColor: '#fff', borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 20, height: '70%', alignItems: 'center' },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', width: '100%', marginBottom: 20 },
  modalTitle: { fontSize: 16, fontWeight: '700' },
  searchBar: { flexDirection: 'row', justifyContent: 'space-between', backgroundColor: '#f1f5f9', width: '100%', padding: 12, borderRadius: 12, marginBottom: 20 },
  jobRow: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 16, borderBottomWidth: 1, borderColor: '#f1f5f9', width: '100%' },
  jobDot: { width: 16, height: 16, borderRadius: 8, backgroundColor: '#3b82f6' },
  jobText: { fontSize: 15, color: '#334155' },
  cancelModalBtn: { marginTop: 20, borderWidth: 1, borderColor: '#cbd5e1', paddingVertical: 12, width: '100%', borderRadius: 12, alignItems: 'center' },
  cancelModalText: { color: '#64748b', fontWeight: '700' }
});
