import React, { useState, useEffect, useContext, useCallback, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, Alert, Modal, ScrollView, Animated } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import * as Location from 'expo-location';
import { WebView } from 'react-native-webview';
import { Ionicons } from '@expo/vector-icons';
import { AuthContext } from '../context/AuthContext';

export default function DashboardScreen() {
  const { user, logout, API_BASE_URL } = useContext(AuthContext);
  const [isClockedIn, setIsClockedIn] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [loading, setLoading] = useState(false);
  const [gpsLoading, setGpsLoading] = useState(false);
  
  // Real dynamic location state (null until verified hardware lock)
  const [location, setLocation] = useState(null);
  const [showJobModal, setShowJobModal] = useState(false);

  // Dynamic Jobs State from API
  const [jobCategories, setJobCategories] = useState([]);
  const [selectedJob, setSelectedJob] = useState('System Administrator');
  const [jobsLoading, setJobsLoading] = useState(false);
  
  const timerRef = useRef(null);
  const webViewRef = useRef(null);
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1.15, duration: 1000, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1.0, duration: 1000, useNativeDriver: true }),
      ])
    ).start();
  }, [pulseAnim]);

  // Fetch dynamic job categories & sub-items from backend API
  const fetchJobs = useCallback(async () => {
    setJobsLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/jobs`);
      if (res.ok) {
        const data = await res.json();
        setJobCategories(data);
        if (data.length > 0 && data[0].sub_items.length > 0) {
          setSelectedJob(data[0].sub_items[0].name);
        }
      }
    } catch (e) {
      console.log('Error fetching jobs:', e);
    }
    setJobsLoading(false);
  }, [API_BASE_URL]);

  const requestGpsLocation = async (showAlertOnFail = false) => {
    setGpsLoading(true);
    try {
      let servicesEnabled = await Location.hasServicesEnabledAsync();
      if (!servicesEnabled) {
        setGpsLoading(false);
        setLocation(null);
        if (showAlertOnFail) {
          Alert.alert('Location Services Disabled', 'Please check your Internet connection and enable Location Services (GPS) on your device.');
        }
        return;
      }

      let { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        setGpsLoading(false);
        setLocation(null);
        if (showAlertOnFail) {
          Alert.alert('Permission Denied', 'Location permission is required to validate your DTR clock-in location.');
        }
        return;
      }

      const locPromise = Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Highest });
      const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error('GPS_TIMEOUT')), 6000));
      const freshLoc = await Promise.race([locPromise, timeoutPromise]);

      if (freshLoc && freshLoc.coords) {
        const liveCoords = {
          latitude: freshLoc.coords.latitude,
          longitude: freshLoc.coords.longitude,
          accuracy: freshLoc.coords.accuracy,
        };
        setLocation(liveCoords);
        updateLeafletMap(liveCoords.latitude, liveCoords.longitude);
      }
    } catch (e) {
      setLocation(null);
      if (showAlertOnFail) {
        Alert.alert('Location Unavailable', 'Could not validate location. Please check your Internet connection or location services.');
      }
    }
    setGpsLoading(false);
  };

  const updateLeafletMap = (lat, lng) => {
    if (webViewRef.current) {
      const jsCode = `
        if (window.map && window.marker) {
          window.map.setView([${lat}], [${lng}], 16);
          window.marker.setLatLng([${lat}], [${lng}]);
        }
        true;
      `;
      webViewRef.current.injectJavaScript(jsCode);
    }
  };

  const fetchStatus = useCallback(async () => {
    if (!user || !user.employee_id) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/punch/active/${user.employee_id}`);
      if (res.ok) {
        const data = await res.json();
        setIsClockedIn(data.is_clocked_in);
        setElapsedSeconds(data.is_clocked_in ? (data.elapsed_seconds || 0) : 0);
        if (data.job_name) {
          const cleanJob = data.job_name.replace('Job: ', '');
          setSelectedJob(cleanJob);
        }
      }
    } catch (e) {}
  }, [user, API_BASE_URL]);

  useFocusEffect(useCallback(() => {
    requestGpsLocation(false);
    fetchJobs();
    fetchStatus();
    const poller = setInterval(fetchStatus, 4000);
    return () => clearInterval(poller);
  }, [fetchStatus, fetchJobs]));

  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (isClockedIn) timerRef.current = setInterval(() => setElapsedSeconds(p => p + 1), 1000);
    return () => clearInterval(timerRef.current);
  }, [isClockedIn]);

  const submitPunch = async (jobName = selectedJob) => {
    if (!location) {
      Alert.alert('Location Error', 'Could not validate location. Please check your Internet connection or location services.');
      return;
    }

    setLoading(true);
    setShowJobModal(false);
    try {
      const res = await fetch(`${API_BASE_URL}/api/punch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          employee_id: user.employee_id,
          punch_type: isClockedIn ? 'CLOCK_OUT' : 'CLOCK_IN',
          latitude: location.latitude,
          longitude: location.longitude,
          accuracy: location.accuracy || 10,
          address: isClockedIn ? 'Shift Ended' : `Job: ${jobName}`,
        }),
      });
      if (res.ok) await fetchStatus();
    } catch (e) {
      Alert.alert('Connection Error', 'Failed to connect to backend server.');
    }
    setLoading(false);
  };

  const formatTime = (ts) => {
    const h = String(Math.floor(ts / 3600)).padStart(2, '0');
    const m = String(Math.floor((ts % 3600) / 60)).padStart(2, '0');
    const s = String(ts % 60).padStart(2, '0');
    return `${h}:${m}:${s}`;
  };

  const initialLat = location ? location.latitude : 14.5764;
  const initialLng = location ? location.longitude : 121.0851;

  const leafletHtml = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
      <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
      <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
      <style>
        body, html, #map { height: 100%; width: 100%; margin: 0; padding: 0; background-color: #0f172a; }
        .leaflet-container { background: #1e293b; }
      </style>
    </head>
    <body>
      <div id="map"></div>
      <script>
        var map = L.map('map', { zoomControl: false, attributionControl: false }).setView([${initialLat}, ${initialLng}], 16);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map);
        var marker = L.marker([${initialLat}, ${initialLng}]).addTo(map);
        window.map = map;
        window.marker = marker;
      </script>
    </body>
    </html>
  `;

  if (isClockedIn) {
    return (
      <View style={styles.activeShiftContainer}>
        <View style={styles.topBar}>
          <TouchableOpacity onPress={logout} style={styles.iconCircleBtn}><Ionicons name="arrow-back" size={20} color="#0f172a" /></TouchableOpacity>
          <Text style={styles.topBarTitle}>Active Duty Shift</Text>
          <View style={styles.livePulseDot} />
        </View>

        <View style={styles.activeCard}>
          <View style={styles.jobPill}>
            <Text style={styles.jobPillText}>{selectedJob}</Text>
          </View>
          <Text style={styles.activeTimer}>{formatTime(elapsedSeconds)}</Text>
          <View style={styles.locRow}>
            <Ionicons name="location" size={14} color="#60a5fa" />
            <Text style={styles.locText}>
              {location ? `GPS Pin: ${location.latitude.toFixed(5)}, ${location.longitude.toFixed(5)}` : 'Location Unavailable'}
            </Text>
          </View>
        </View>

        <ScrollView style={styles.detailsList}>
          <Text style={styles.detailsTitle}>Shift Actions & Log</Text>
          {['Location Verification', 'Duty Note', 'Break Log'].map((item, i) => (
            <View key={i} style={styles.detailItem}>
              <View style={{flexDirection: 'row', alignItems: 'center', gap: 10}}>
                <Ionicons name="checkmark-circle-outline" size={20} color="#2563eb" />
                <Text style={styles.detailText}>{item}</Text>
              </View>
              <TouchableOpacity style={styles.uploadBtn}><Text style={styles.uploadText}>Update</Text></TouchableOpacity>
            </View>
          ))}
        </ScrollView>

        <View style={styles.bottomActions}>
          <TouchableOpacity style={styles.switchJobBtn} onPress={() => setShowJobModal(true)}>
            <Text style={styles.switchJobText}>Switch Role</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.endShiftBtn} onPress={() => submitPunch()} disabled={loading}>
            {loading ? <ActivityIndicator color="#fff"/> : <Text style={styles.endShiftText}>Clock Out</Text>}
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Header Profile Info */}
      <View style={styles.headerAbsolute}>
        <View style={styles.headerInfo}>
          <View style={styles.avatar}><Text style={{color:'#fff', fontWeight: '700'}}>{user?.name?.charAt(0) || 'U'}</Text></View>
          <View>
            <Text style={styles.greeting}>{user?.name}</Text>
            <Text style={styles.subGreeting}>{user?.position || 'Staff'} • {user?.department || 'Operations'}</Text>
          </View>
        </View>
        <TouchableOpacity onPress={logout} style={styles.logoutIconBtn}>
          <Ionicons name="log-out-outline" size={22} color="#475569"/>
        </TouchableOpacity>
      </View>

      {/* Map View */}
      <WebView
        ref={webViewRef}
        style={styles.mapFullscreen}
        originWhitelist={['*']}
        source={{ html: leafletHtml }}
        scrollEnabled={true}
      />

      {/* Manual Recenter FAB Button */}
      <TouchableOpacity style={styles.recenterFab} onPress={() => requestGpsLocation(true)}>
        {gpsLoading ? <ActivityIndicator size="small" color="#2563eb" /> : <Ionicons name="locate" size={24} color="#2563eb" />}
      </TouchableOpacity>

      {/* Clock-In Bottom Sheet */}
      <View style={styles.bottomDrawer}>
        <Animated.View style={[styles.clockBtnWrapper, { transform: [{ scale: pulseAnim }] }]}>
          <TouchableOpacity 
            style={[styles.bigClockBtn, !location && { backgroundColor: '#94a3b8' }]} 
            onPress={() => location ? setShowJobModal(true) : requestGpsLocation(true)} 
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator size="large" color="#ffffff" />
            ) : (
              <>
                <Ionicons name="finger-print-outline" size={44} color="#ffffff" />
                <Text style={styles.bigClockText}>{location ? 'CLOCK IN' : 'RE-TRY GPS'}</Text>
              </>
            )}
          </TouchableOpacity>
        </Animated.View>
        
        <View style={styles.quickStatsRow}>
          <View style={styles.statBox}>
            <Ionicons name="time-outline" size={18} color="#2563eb" />
            <Text style={styles.statLabel}>Schedule</Text>
            <Text style={styles.statVal}>8:00 AM - 5:00 PM</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statBox}>
            <Ionicons name="location-outline" size={18} color={location ? "#16a34a" : "#ef4444"} />
            <Text style={styles.statLabel}>Location Status</Text>
            <Text style={[styles.statVal, { color: location ? "#16a34a" : "#ef4444" }]}>
              {location ? `${location.latitude.toFixed(4)}, ${location.longitude.toFixed(4)}` : 'Check GPS / Network'}
            </Text>
          </View>
        </View>
      </View>

      {/* Dynamic Role Selection Modal Sheet */}
      <Modal visible={showJobModal} transparent animationType="slide">
        <View style={styles.modalBg}>
          <View style={styles.modalSheet}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Select Duty Role</Text>
              <TouchableOpacity onPress={() => setShowJobModal(false)}><Ionicons name="close" size={24} color="#475569" /></TouchableOpacity>
            </View>

            {jobsLoading ? (
              <ActivityIndicator size="large" color="#2563eb" style={{ marginVertical: 40 }} />
            ) : (
              <ScrollView style={{ width: '100%' }}>
                {jobCategories.map((cat) => (
                  <View key={cat.id} style={{ marginBottom: 16 }}>
                    <Text style={styles.categoryHeader}>{cat.name}</Text>
                    {cat.sub_items.map((sub) => (
                      <TouchableOpacity 
                        key={sub.id} 
                        style={styles.jobRow} 
                        onPress={() => { setSelectedJob(sub.name); submitPunch(sub.name); }}
                      >
                        <View style={styles.jobDot}/>
                        <Text style={styles.jobText}>{sub.name}</Text>
                        <Ionicons name="chevron-forward" size={18} color="#cbd5e1" />
                      </TouchableOpacity>
                    ))}
                  </View>
                ))}
              </ScrollView>
            )}
          </View>
        </View>
      </Modal>

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  headerAbsolute: { position: 'absolute', top: 44, left: 16, right: 16, zIndex: 10, flexDirection: 'row', justifyContent: 'space-between', backgroundColor: 'rgba(255,255,255,0.96)', padding: 12, borderRadius: 20, alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.15, shadowRadius: 8, elevation: 6 },
  headerInfo: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  avatar: { width: 42, height: 42, borderRadius: 21, backgroundColor: '#2563eb', alignItems: 'center', justifyContent: 'center' },
  greeting: { fontWeight: '700', fontSize: 16, color: '#0f172a' },
  subGreeting: { fontSize: 11, color: '#64748b' },
  logoutIconBtn: { padding: 8, borderRadius: 12, backgroundColor: '#f1f5f9' },
  mapFullscreen: { flex: 1, width: '100%' },
  recenterFab: { position: 'absolute', right: 20, bottom: 210, width: 48, height: 48, borderRadius: 24, backgroundColor: '#ffffff', justifyContent: 'center', alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.2, shadowRadius: 6, elevation: 8, zIndex: 12 },
  bottomDrawer: { position: 'absolute', bottom: 0, width: '100%', backgroundColor: '#ffffff', borderTopLeftRadius: 32, borderTopRightRadius: 32, paddingBottom: 32, paddingTop: 50, alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.15, shadowRadius: 12, elevation: 12 },
  clockBtnWrapper: { position: 'absolute', top: -55, alignSelf: 'center', backgroundColor: '#ffffff', borderRadius: 70, padding: 8, shadowColor: '#2563eb', shadowOpacity: 0.35, shadowRadius: 12, elevation: 10 },
  bigClockBtn: { width: 124, height: 124, borderRadius: 62, backgroundColor: '#2563eb', alignItems: 'center', justifyContent: 'center' },
  bigClockText: { color: '#ffffff', fontWeight: '800', fontSize: 14, marginTop: 4, letterSpacing: 0.5 },
  quickStatsRow: { flexDirection: 'row', width: '90%', justifyContent: 'space-around', marginTop: 16, backgroundColor: '#f8fafc', padding: 14, borderRadius: 18, alignItems: 'center' },
  statBox: { alignItems: 'center', flex: 1 },
  statDivider: { width: 1, height: 28, backgroundColor: '#e2e8f0' },
  statLabel: { fontSize: 11, color: '#64748b', marginTop: 4 },
  statVal: { fontSize: 12, fontWeight: '700', color: '#0f172a', marginTop: 2 },
  
  // Shift Active Layout
  activeShiftContainer: { flex: 1, backgroundColor: '#f8fafc', paddingTop: 48 },
  topBar: { flexDirection: 'row', justifyContent: 'space-between', paddingHorizontal: 20, marginBottom: 20, alignItems: 'center' },
  iconCircleBtn: { padding: 8, borderRadius: 20, backgroundColor: '#ffffff', shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 4, elevation: 2 },
  topBarTitle: { fontSize: 17, fontWeight: '700', color: '#0f172a' },
  livePulseDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: '#22c55e' },
  activeCard: { backgroundColor: '#0f172a', marginHorizontal: 20, borderRadius: 24, padding: 24, alignItems: 'center' },
  jobPill: { backgroundColor: 'rgba(255,255,255,0.12)', paddingHorizontal: 16, paddingVertical: 6, borderRadius: 20, marginBottom: 14 },
  jobPillText: { color: '#38bdf8', fontSize: 12, fontWeight: '700' },
  activeTimer: { fontSize: 44, fontWeight: '800', color: '#ffffff', marginBottom: 14, letterSpacing: 1 },
  locRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  locText: { color: '#94a3b8', fontSize: 12 },
  detailsList: { flex: 1, padding: 20 },
  detailsTitle: { fontSize: 15, fontWeight: '700', color: '#0f172a', marginBottom: 16 },
  detailItem: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 14, borderBottomWidth: 1, borderColor: '#e2e8f0' },
  detailText: { fontSize: 14, color: '#334155', fontWeight: '500' },
  uploadBtn: { borderWidth: 1, borderColor: '#cbd5e1', paddingHorizontal: 14, paddingVertical: 6, borderRadius: 14, backgroundColor: '#ffffff' },
  uploadText: { fontSize: 12, color: '#2563eb', fontWeight: '600' },
  bottomActions: { flexDirection: 'row', padding: 20, gap: 12, backgroundColor: '#ffffff', borderTopWidth: 1, borderColor: '#f1f5f9' },
  switchJobBtn: { flex: 1, backgroundColor: '#f1f5f9', height: 50, borderRadius: 16, justifyContent: 'center', alignItems: 'center' },
  switchJobText: { color: '#2563eb', fontWeight: '700' },
  endShiftBtn: { flex: 1.5, backgroundColor: '#ef4444', height: 50, borderRadius: 16, justifyContent: 'center', alignItems: 'center' },
  endShiftText: { color: '#ffffff', fontWeight: '700' },

  // Modal Sheet
  modalBg: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' },
  modalSheet: { backgroundColor: '#ffffff', borderTopLeftRadius: 28, borderTopRightRadius: 28, padding: 24, height: '55%', alignItems: 'center' },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', width: '100%', marginBottom: 20, alignItems: 'center' },
  modalTitle: { fontSize: 18, fontWeight: '700', color: '#0f172a' },
  categoryHeader: { fontSize: 12, fontWeight: '700', color: '#64748b', textTransform: 'uppercase', marginBottom: 8, letterSpacing: 0.5 },
  jobRow: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 14, borderBottomWidth: 1, borderColor: '#f1f5f9', width: '100%', justifyContent: 'space-between' },
  jobDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: '#2563eb' },
  jobText: { fontSize: 14, color: '#334155', fontWeight: '600', flex: 1 }
});
