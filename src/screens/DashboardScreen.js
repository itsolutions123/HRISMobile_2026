import React, { useState, useEffect, useContext, useCallback, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, Alert, Modal, ScrollView, Animated, TextInput , Platform } from 'react-native';
import DateTimePicker from '@react-native-community/datetimepicker';
import { useFocusEffect } from '@react-navigation/native';
import * as Location from 'expo-location';
import { WebView } from 'react-native-webview';
import { Ionicons } from '@expo/vector-icons';
import { AuthContext } from '../context/AuthContext';

export default function DashboardScreen({ navigation }) {
  const { user, token, logout, API_BASE_URL } = useContext(AuthContext);
  const [isClockedIn, setIsClockedIn] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [loading, setLoading] = useState(false);
  const [gpsLoading, setGpsLoading] = useState(false);

  // Dynamic location state
  const [location, setLocation] = useState(null);
  const [clockOutLocation, setClockOutLocation] = useState(null);

  // Modals
  const [showJobModal, setShowJobModal] = useState(false);
  const [showClockOutReviewModal, setShowClockOutReviewModal] = useState(false);
  const [showEditInModal, setShowEditInModal] = useState(false);
  const [showEditOutModal, setShowEditOutModal] = useState(false);
  const [showEditHistoryModal, setShowEditHistoryModal] = useState(false);

  // Job & Edit States
  const [deptJobTitles, setDeptJobTitles] = useState([]);
  const [selectedJob, setSelectedJob] = useState('Staff');
  const [jobsLoading, setJobsLoading] = useState(false);

  const [clockInTimestampStr, setClockInTimestampStr] = useState('');
  const [clockOutTimestampStr, setClockOutTimestampStr] = useState('');
  const [requestedInTime, setRequestedInTime] = useState('');
  const [requestedOutTime, setRequestedOutTime] = useState('');
  const [editReason, setEditReason] = useState('');
  const [attachedFileName, setAttachedFileName] = useState('');
  const [editHistoryLogs, setEditHistoryModalLogs] = useState([]);
  const [isShiftEdited, setIsShiftEdited] = useState(false);

  const timerRef = useRef(null);
  const webViewRef = useRef(null);
  const clockOutWebViewRef = useRef(null);
  const pulseAnim = useRef(new Animated.Value(1)).current;

  const userDept = user?.department || 'HO - IT';

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1.15, duration: 1000, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1.0, duration: 1000, useNativeDriver: true }),
      ])
    ).start();
  }, [pulseAnim]);

  const fetchJobs = useCallback(async () => {
    setJobsLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/jobs`, { headers: { 'Authorization': 'Bearer ' + token } });
      let titles = [];
      if (res.ok) {
        const data = await res.json();
        const match = data.find(c => 
          c.code === userDept || 
          c.name === userDept || 
          c.description === userDept ||
          c.name.toLowerCase() === userDept.toLowerCase()
        );
        if (match && match.sub_items && match.sub_items.length > 0) {
          titles = match.sub_items.map(s => s.name);
        }
      }

      if (titles.length === 0) {
        const deptUpper = userDept.toUpperCase();
        if (deptUpper.includes('MARKETING')) {
          titles = ['Marketing OIC', 'BME'];
        } else if (deptUpper.includes('ADMIN')) {
          titles = ['Admin OIC', 'Payroll Specialist', 'Admin Assistant', 'Messenger'];
        } else if (deptUpper.includes('HR') || deptUpper.includes('HUMAN RESOURCE')) {
          titles = ['HR Manager', 'HR Associate', 'Recruiter'];
        } else if (deptUpper.includes('ACCOUNTING')) {
          titles = ['Accounting Head', 'Junior Accountant', 'Billing Clerk'];
        } else if (deptUpper.includes('SALES')) {
          titles = ['Sales Manager', 'Sales Executive'];
        } else {
          titles = ['System Administrator', 'IT Head', 'Technical Specialist'];
        }
      }

      setDeptJobTitles(titles);
      if (titles.length > 0) setSelectedJob(titles[0]);
    } catch (e) {
      setDeptJobTitles(['System Administrator', 'IT Head', 'Technical Specialist']);
      setSelectedJob('System Administrator');
    }
    setJobsLoading(false);
  }, [API_BASE_URL, userDept]);

  const requestGpsLocation = async (isForClockOut = false, showAlertOnFail = false) => {
    setGpsLoading(true);
    try {
      let servicesEnabled = await Location.hasServicesEnabledAsync();
      if (!servicesEnabled) {
        setGpsLoading(false);
        if (isForClockOut) setClockOutLocation(null); else setLocation(null);
        if (showAlertOnFail) {
          Alert.alert('Location Services Disabled', 'Please enable Location Services (GPS) on your device.');
        }
        return;
      }

      let { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        setGpsLoading(false);
        if (isForClockOut) setClockOutLocation(null); else setLocation(null);
        if (showAlertOnFail) {
          Alert.alert('Permission Denied', 'Location permission is required to validate DTR clock location.');
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
        if (isForClockOut) {
          setClockOutLocation(liveCoords);
          updateClockOutMap(liveCoords.latitude, liveCoords.longitude);
        } else {
          setLocation(liveCoords);
          updateLeafletMap(liveCoords.latitude, liveCoords.longitude);
        }
      }
    } catch (e) {
      if (isForClockOut) setClockOutLocation(null); else setLocation(null);
      if (showAlertOnFail) {
        Alert.alert('Location Unavailable', 'Could not validate GPS location. Please check your location settings.');
      }
    }
    setGpsLoading(false);
  };

  const updateLeafletMap = (lat, lng) => {
    if (webViewRef.current) {
      const jsCode = `if (window.map && window.marker) { window.map.setView([${lat}], [${lng}], 16); window.marker.setLatLng([${lat}], [${lng}]); } true;`;
      webViewRef.current.injectJavaScript(jsCode);
    }
  };

  const updateClockOutMap = (lat, lng) => {
    if (clockOutWebViewRef.current) {
      const jsCode = `if (window.map && window.marker) { window.map.setView([${lat}], [${lng}], 16); window.marker.setLatLng([${lat}], [${lng}]); } true;`;
      clockOutWebViewRef.current.injectJavaScript(jsCode);
    }
  };

  const fetchStatus = useCallback(async () => {
    if (!user || !user.employee_id) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/punch/active/me`, { headers: { 'Authorization': 'Bearer ' + token } });
      if (res.ok) {
        const data = await res.json();
        setIsClockedIn(data.is_clocked_in);
        setElapsedSeconds(data.is_clocked_in ? (data.elapsed_seconds || 0) : 0);
        if (data.clock_in_time) setClockInTimestampStr(data.clock_in_time);
        if (data.job_name) {
          const cleanJob = data.job_name.replace('Job: ', '').split(' (')[0];
          setSelectedJob(cleanJob);
        }
      }
    } catch (e) {}
  }, [user, API_BASE_URL]);

  useFocusEffect(useCallback(() => {
    requestGpsLocation(false, false);
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

  const [tempEditDate, setTempEditDate] = useState(new Date());
  const [showPicker, setShowPicker] = useState(false);
  const [activePickerType, setActivePickerType] = useState('IN');

  const openTimePicker = (type, currentStr) => {
    setActivePickerType(type);
    let d = new Date();
    try {
      const match = (currentStr || '').match(/(\d+):(\d+)\s*(AM|PM)/i);
      if (match) {
        let hrs = parseInt(match[1]);
        const mins = parseInt(match[2]);
        const isPM = match[3].toUpperCase() === 'PM';
        if (isPM && hrs < 12) hrs += 12;
        if (!isPM && hrs === 12) hrs = 0;
        d.setHours(hrs, mins, 0);
      }
    } catch(e) {}
    setTempEditDate(d);
    setShowPicker(true);
  };

  const handleTimeChange = (event, selectedDate) => {
    if (Platform.OS === 'android') setShowPicker(false);
    if (selectedDate) {
      setTempEditDate(selectedDate);
      const str = selectedDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      if (activePickerType === 'IN') setRequestedInTime(str);
      else setRequestedOutTime(str);
    }
  };

  const handleOpenClockOutReview = () => {
    const now = new Date();
    const formattedOut = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    setClockOutTimestampStr(formattedOut);
    setShowClockOutReviewModal(true);
    requestGpsLocation(true, true);
  };

  const submitPunch = async (jobName = selectedJob) => {
    const locToUse = isClockedIn ? clockOutLocation : location;
    if (!locToUse) {
      Alert.alert('Location Required', 'GPS location verification is required before confirming clock out. Please tap "Refresh Location".');
      return;
    }

    setLoading(true);
    setShowJobModal(false);
    setShowClockOutReviewModal(false);

    const now = new Date();
    const currentDate = now.toISOString().split('T')[0];
    const currentTimestamp = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    try {
      const res = await fetch(`${API_BASE_URL}/api/punch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
        body: JSON.stringify({
          employee_id: user.employee_id,
          full_name: user?.name || (user?.first_name ? `${user?.first_name} ${user?.last_name || ''}` : user.employee_id),
          department: userDept,
          brand_subgroup: userDept,
          job_title: jobName,
          punch_type: isClockedIn ? 'CLOCK_OUT' : 'CLOCK_IN',
          latitude: locToUse.latitude,
          longitude: locToUse.longitude,
          accuracy: locToUse.accuracy || 10,
          date: currentDate,
          timestamp: currentTimestamp,
          address: isClockedIn ? 'Shift Ended' : `Job: ${jobName} (${userDept})`,
        }),
      });
      if (res.ok) await fetchStatus();
    } catch (e) {
      Alert.alert('Connection Error', 'Failed to connect to backend server.');
    }
    setLoading(false);
  };

  const handleSendShiftRevision = async (punchType) => {
    const timeVal = punchType === 'CLOCK_IN' ? requestedInTime : requestedOutTime;
    if (!timeVal.trim() || !editReason.trim()) {
      Alert.alert('Missing Fields', 'Please enter the requested time and reason for the edit.');
      return;
    }

    try {
      const headers = { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) };
      const res = await fetch(`${API_BASE_URL}/api/manager/revisions/request`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          requested_punch_type: punchType,
          requested_timestamp: timeVal,
          reason: editReason,
          attachment_note: attachedFileName
        })
      });

      if (res.ok) {
        Alert.alert('Edit Shift Request Sent', 'Your shift edit request has been sent to your sub-group manager/admin for approval.');
        setIsShiftEdited(true);
        const newLog = `${punchType}: Requested ${timeVal} — Reason: ${editReason} ${attachedFileName ? `(Attached: ${attachedFileName})` : ''}`;
        setEditHistoryModalLogs(prev => [newLog, ...prev]);
        setShowEditInModal(false);
        setShowEditOutModal(false);
      } else {
        Alert.alert('Request Failed', 'Failed to submit shift edit request.');
      }
    } catch(e) {
      Alert.alert('Error', 'Could not connect to backend server.');
    }
  };

  const formatTime = (ts) => {
    const h = String(Math.floor(ts / 3600)).padStart(2, '0');
    const m = String(Math.floor((ts % 3600) / 60)).padStart(2, '0');
    const s = String(ts % 60).padStart(2, '0');
    return `${h}:${m}:${s}`;
  };

  const activeLat = (isClockedIn ? clockOutLocation?.latitude : location?.latitude) || 14.5764;
  const activeLng = (isClockedIn ? clockOutLocation?.longitude : location?.longitude) || 121.0851;

  const leafletHtml = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
      <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
      <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
      <style>body, html, #map { height: 100%; width: 100%; margin: 0; padding: 0; background-color: #0f172a; }</style>
    </head>
    <body>
      <div id="map"></div>
      <script>
        var map = L.map('map', { zoomControl: false, attributionControl: false }).setView([${activeLat}, ${activeLng}], 16);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map);
        var marker = L.marker([${activeLat}, ${activeLng}]).addTo(map);
        window.map = map; window.marker = marker;
      </script>
    </body>
    </html>
  `;

  return (
    <View style={styles.container}>
      {/* HEADER PROFILE INFO REMOVED */}

      {/* CLOCKED IN / ACTIVE SHIFT VIEW */}
      {isClockedIn ? (
        <View style={styles.activeShiftContainer}>
          <View style={styles.activeCard}>
            <View style={styles.jobPill}>
              <Text style={styles.jobPillText}>{selectedJob} • {userDept}</Text>
            </View>
            <Text style={styles.activeTimer}>{formatTime(elapsedSeconds)}</Text>
            <View style={styles.locRow}>
              <Ionicons name="location" size={14} color="#60a5fa" />
              <Text style={styles.locText}>
                {location ? `GPS Pin: ${location.latitude.toFixed(5)}, ${location.longitude.toFixed(5)}` : 'Location Locked'}
              </Text>
            </View>
          </View>

          <ScrollView style={styles.detailsList}>
            <Text style={styles.sectionTitle}>Attachments</Text>
            <TouchableOpacity style={styles.addNoteBtn}>
              <Text style={styles.addNoteText}>{'>'} Add note</Text>
            </TouchableOpacity>

            <View style={styles.contentDivider} />

            <View style={{flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12}}>
              <Text style={styles.sectionTitle}>Shift Logs</Text>
              {isShiftEdited && (
                <TouchableOpacity style={styles.editedBadge} onPress={() => setShowEditHistoryModal(true)}>
                  <Ionicons name="alert-circle-outline" size={13} color="#d97706" />
                  <Text style={styles.editedBadgeText}>Edited (History)</Text>
                </TouchableOpacity>
              )}
            </View>
            <Text style={styles.logPlaceholderText}>{/* {user activity} */}User clocked in.</Text>
          </ScrollView>

          <View style={styles.bottomActions}>
            <TouchableOpacity style={styles.switchJobBtn} onPress={() => setShowJobModal(true)}>
              <Ionicons name="swap-horizontal" size={18} color="#3b82f6" style={{marginRight: 6}} />
              <Text style={styles.switchJobText}>Switch Role</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.endShiftBtn} onPress={handleOpenClockOutReview} disabled={loading}>
              <Ionicons name="exit-outline" size={18} color="#ffffff" style={{marginRight: 6}} />
              <Text style={styles.endShiftText}>Clock Out</Text>
            </TouchableOpacity>
          </View>
        </View>
      ) : (
        /* CLOCKED OUT VIEW WITH FULL MAP */
        <>
          <WebView
            ref={webViewRef}
            style={styles.mapFullscreen}
            originWhitelist={['*']}
            source={{ html: leafletHtml }}
            scrollEnabled={true}
          />

          <View style={styles.bottomDrawer}>
            <TouchableOpacity style={styles.recenterFab} onPress={() => requestGpsLocation(false, true)}>
              {gpsLoading ? <ActivityIndicator size="small" color="#0f172a" /> : <Ionicons name="locate" size={24} color="#0f172a" />}
            </TouchableOpacity>

            <Animated.View style={[styles.clockBtnWrapper, { transform: [{ scale: pulseAnim }] }]}>
              <TouchableOpacity
                style={[styles.bigClockBtn, !location && { backgroundColor: '#94a3b8' }]}
                onPress={() => location ? setShowJobModal(true) : requestGpsLocation(false, true)}
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
                <Ionicons name="location-outline" size={18} color={location ? "#16a34a" : "#ef4444"} />
                <Text style={styles.statLabel}>Location Status</Text>
                <Text style={[styles.statVal, { color: location ? "#16a34a" : "#ef4444" }]}>
                  {location ? `${location.latitude.toFixed(4)}, ${location.longitude.toFixed(4)}` : 'Check GPS / Network'}
                </Text>
              </View>
            </View>
          </View>
        </>
      )}

      {/* CLOCK OUT REVIEW & GPS CONFIRMATION MODAL */}
      <Modal visible={showClockOutReviewModal} transparent animationType="slide">
        <View style={styles.modalBg}>
          <View style={[styles.modalSheet, { height: '85%' }]}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Shift Review</Text>
              <TouchableOpacity onPress={() => setShowClockOutReviewModal(false)}><Ionicons name="close" size={24} color="#475569" /></TouchableOpacity>
            </View>

            <ScrollView style={{ width: '100%' }} showsVerticalScrollIndicator={false}>
              <View style={styles.clockOutMapCard}>
                <WebView
                  ref={clockOutWebViewRef}
                  style={{ flex: 1, borderRadius: 16 }}
                  originWhitelist={['*']}
                  source={{ html: leafletHtml }}
                />
                <TouchableOpacity style={styles.refreshLocBtn} onPress={() => requestGpsLocation(true, true)}>
                  {gpsLoading ? <ActivityIndicator size="small" color="#2563eb" /> : <Ionicons name="refresh" size={18} color="#2563eb" />}
                  <Text style={styles.refreshLocText}>Refresh Location</Text>
                </TouchableOpacity>
              </View>

              <View style={styles.punchReviewBlock}>
                <Text style={styles.punchReviewLabel}>CLOCK IN</Text>
                <View style={styles.punchReviewDataRow}>
                  <Text style={styles.punchReviewVal}>{new Date().toISOString().split('T')[0]}, {clockInTimestampStr || '08:00 AM'}</Text>
                  <TouchableOpacity style={styles.editBtnBox} onPress={() => { setRequestedInTime(clockInTimestampStr); setShowEditInModal(true); }}>
                    <Text style={styles.editBtnBoxText}>EDIT</Text>
                  </TouchableOpacity>
                </View>
              </View>

              <View style={styles.punchReviewBlock}>
                <Text style={styles.punchReviewLabel}>CLOCK OUT</Text>
                <View style={styles.punchReviewDataRow}>
                  <Text style={styles.punchReviewVal}>{new Date().toISOString().split('T')[0]}, {clockOutTimestampStr || '05:00 PM'}</Text>
                  <TouchableOpacity style={styles.editBtnBox} onPress={() => { setRequestedOutTime(clockOutTimestampStr); setShowEditOutModal(true); }}>
                    <Text style={styles.editBtnBoxText}>EDIT</Text>
                  </TouchableOpacity>
                </View>
              </View>

              <TouchableOpacity style={styles.confirmClockOutBtn} onPress={() => submitPunch(selectedJob)} disabled={loading}>
                {loading ? <ActivityIndicator color="#ffffff" /> : <Text style={styles.confirmClockOutText}>CONFIRM SHIFT</Text>}
              </TouchableOpacity>
            </ScrollView>
          </View>
        </View>
      </Modal>

      {/* EDIT CLOCK IN MODAL */}
      <Modal visible={showEditInModal} transparent animationType="fade">
        <View style={styles.modalBg}>
          <View style={[styles.modalSheet, { height: 'auto', paddingBottom: 30 }]}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Edit Clock In</Text>
              <TouchableOpacity onPress={() => setShowEditInModal(false)}><Ionicons name="close" size={24} color="#475569" /></TouchableOpacity>
            </View>
            
            <TouchableOpacity style={[styles.modalInput, { justifyContent: 'center' }]} onPress={() => openTimePicker('IN', requestedInTime)}>
              <Text style={{ fontSize: 14, color: '#0f172a' }}>{requestedInTime || 'Tap to select time'}</Text>
            </TouchableOpacity>
            {(showPicker && Platform.OS === 'ios' && activePickerType === 'IN') && (
              <DateTimePicker value={tempEditDate} mode="time" display="spinner" onChange={handleTimeChange} style={{alignSelf: 'center', width: '100%', height: 120}} />
            )}

            <Text style={styles.editModalLabel}>Note:</Text>
            <TextInput style={[styles.modalInput, { height: 80 }]} value={editReason} onChangeText={setEditReason} placeholder="Enter note / reason..." multiline />
            
            <TouchableOpacity style={styles.confirmClockOutBtn} onPress={() => handleSendShiftRevision('CLOCK_IN')}>
              <Text style={styles.confirmClockOutText}>SAVE EDIT</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* EDIT CLOCK OUT MODAL */}
      <Modal visible={showEditOutModal} transparent animationType="fade">
        <View style={styles.modalBg}>
          <View style={[styles.modalSheet, { height: 'auto', paddingBottom: 30 }]}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Edit Clock Out</Text>
              <TouchableOpacity onPress={() => setShowEditOutModal(false)}><Ionicons name="close" size={24} color="#475569" /></TouchableOpacity>
            </View>
            
            <TouchableOpacity style={[styles.modalInput, { justifyContent: 'center' }]} onPress={() => openTimePicker('OUT', requestedOutTime)}>
              <Text style={{ fontSize: 14, color: '#0f172a' }}>{requestedOutTime || 'Tap to select time'}</Text>
            </TouchableOpacity>
            {(showPicker && Platform.OS === 'ios' && activePickerType === 'OUT') && (
              <DateTimePicker value={tempEditDate} mode="time" display="spinner" onChange={handleTimeChange} style={{alignSelf: 'center', width: '100%', height: 120}} />
            )}

            <Text style={styles.editModalLabel}>Note:</Text>
            <TextInput style={[styles.modalInput, { height: 80 }]} value={editReason} onChangeText={setEditReason} placeholder="Enter note / reason..." multiline />
            
            <TouchableOpacity style={styles.confirmClockOutBtn} onPress={() => handleSendShiftRevision('CLOCK_OUT')}>
              <Text style={styles.confirmClockOutText}>SAVE EDIT</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* ANDROID FLOATING TIME PICKER */}
      {(showPicker && Platform.OS === 'android') && (
        <DateTimePicker value={tempEditDate} mode="time" display="spinner" onChange={handleTimeChange} />
      )}

      {/* EDIT HISTORY POPUP MODAL */}
      <Modal visible={showEditHistoryModal} transparent animationType="slide">
        <View style={styles.modalBg}>
          <View style={styles.modalSheet}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Shift Revision Edit History</Text>
              <TouchableOpacity onPress={() => setShowEditHistoryModal(false)}><Ionicons name="close" size={24} color="#475569" /></TouchableOpacity>
            </View>
            <ScrollView style={{ width: '100%' }}>
              {editHistoryLogs.length > 0 ? (
                editHistoryLogs.map((log, idx) => (
                  <View key={idx} style={styles.historyLogItem}>
                    <Ionicons name="document-text-outline" size={18} color="#d97706" />
                    <Text style={styles.historyLogText}>{log}</Text>
                  </View>
                ))
              ) : (
                <Text style={{ textAlign: 'center', color: '#94a3b8', marginVertical: 20 }}>No edit history records logged yet.</Text>
              )}
            </ScrollView>
          </View>
        </View>
      </Modal>

      {/* DYNAMIC ROLE SELECTION MODAL */}
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
                <View style={{ marginBottom: 16 }}>
                  <Text style={styles.categoryHeader}>{userDept.toUpperCase()}</Text>
                  {deptJobTitles.map((jobTitle, idx) => (
                    <TouchableOpacity
                      key={idx}
                      style={styles.jobRow}
                      onPress={() => { setSelectedJob(jobTitle); submitPunch(jobTitle); }}
                    >
                      <View style={styles.jobDot}/>
                      <Text style={styles.jobText}>{jobTitle}</Text>
                      <Ionicons name="chevron-forward" size={18} color="#cbd5e1" />
                    </TouchableOpacity>
                  ))}
                </View>
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
  recenterFab: { position: 'absolute', right: 24, top: -24, width: 48, height: 48, borderRadius: 24, backgroundColor: '#ffffff', justifyContent: 'center', alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.15, shadowRadius: 6, elevation: 10, zIndex: 12 },
  bottomDrawer: { position: 'absolute', bottom: 0, width: '100%', backgroundColor: '#ffffff', borderTopWidth: 1, borderColor: '#e2e8f0', paddingBottom: 34, paddingTop: 55, alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.15, shadowRadius: 12, elevation: 12 },
  clockBtnWrapper: { position: 'absolute', top: -65, alignSelf: 'center', backgroundColor: '#ffffff', borderRadius: 75, padding: 8, shadowColor: '#2563eb', shadowOpacity: 0.2, shadowRadius: 12, elevation: 10 },
  bigClockBtn: { width: 130, height: 130, borderRadius: 65, backgroundColor: '#2563eb', alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: '#ffffff' },
  bigClockText: { color: '#ffffff', fontWeight: '800', fontSize: 14, marginTop: 4, letterSpacing: 0.5 },
  quickStatsRow: { flexDirection: 'row', width: '90%', justifyContent: 'space-around', marginTop: 16, backgroundColor: '#f8fafc', padding: 14, borderRadius: 18, alignItems: 'center' },
  statBox: { alignItems: 'center', flex: 1 },
  statDivider: { width: 1, height: 28, backgroundColor: '#e2e8f0' },
  statLabel: { fontSize: 11, color: '#64748b', marginTop: 4 },
  statVal: { fontSize: 12, fontWeight: '700', color: '#0f172a', marginTop: 2 },

  // Shift Active Layout
  activeShiftContainer: { flex: 1, backgroundColor: '#ffffff', paddingTop: 24 },
  activeCard: { backgroundColor: '#0f172a', marginHorizontal: 16, borderRadius: 20, paddingVertical: 28, paddingHorizontal: 24, alignItems: 'center' },
  jobPill: { backgroundColor: 'rgba(255,255,255,0.12)', paddingHorizontal: 16, paddingVertical: 6, borderRadius: 16, marginBottom: 16 },
  jobPillText: { color: '#60a5fa', fontSize: 12, fontWeight: '500' },
  activeTimer: { fontSize: 46, fontWeight: '700', color: '#ffffff', marginBottom: 16, letterSpacing: 1 },
  locRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  locText: { color: '#94a3b8', fontSize: 12 },
  detailsList: { flex: 1, paddingHorizontal: 20, paddingTop: 24 },
  sectionTitle: { fontSize: 16, fontWeight: '600', color: '#0f172a' },
  addNoteBtn: { paddingVertical: 8, marginTop: 4 },
  addNoteText: { fontSize: 15, color: '#334155', fontWeight: '400' },
  contentDivider: { height: 1, backgroundColor: '#e2e8f0', marginVertical: 20 },
  logPlaceholderText: { fontSize: 14, color: '#64748b', fontStyle: 'italic', marginTop: 4 },
  bottomActions: { flexDirection: 'row', paddingHorizontal: 16, paddingTop: 16, paddingBottom: 24, gap: 12, backgroundColor: '#ffffff', borderTopWidth: 1, borderColor: '#f1f5f9' },
  switchJobBtn: { flex: 1, backgroundColor: '#f8fafc', height: 50, borderRadius: 12, justifyContent: 'center', alignItems: 'center', flexDirection: 'row', borderWidth: 1, borderColor: '#e2e8f0' },
  switchJobText: { color: '#3b82f6', fontWeight: '600', fontSize: 14 },
  endShiftBtn: { flex: 1.5, backgroundColor: '#ef4444', height: 50, borderRadius: 12, justifyContent: 'center', alignItems: 'center', flexDirection: 'row' },
  endShiftText: { color: '#ffffff', fontWeight: '600', fontSize: 14 },

  // Fixed Bottom Navigation Tab Bar (Removed)

  // Modal Sheet & Review Modal
  modalBg: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' },
  modalSheet: { backgroundColor: '#ffffff', borderTopLeftRadius: 28, borderTopRightRadius: 28, padding: 24, height: '55%', alignItems: 'center' },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', width: '100%', marginBottom: 16, alignItems: 'center' },
  modalTitle: { fontSize: 18, fontWeight: '700', color: '#0f172a' },
  categoryHeader: { fontSize: 12, fontWeight: '700', color: '#64748b', textTransform: 'uppercase', marginBottom: 8, letterSpacing: 0.5 },
  jobRow: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 14, borderBottomWidth: 1, borderColor: '#f1f5f9', width: '100%', justifyContent: 'space-between' },
  jobDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: '#2563eb' },
  jobText: { fontSize: 14, color: '#334155', fontWeight: '600', flex: 1 },

  clockOutMapCard: { height: 200, width: '100%', borderRadius: 16, overflow: 'hidden', marginBottom: 16, borderWidth: 1, borderColor: '#e2e8f0' },
  refreshLocBtn: { position: 'absolute', bottom: 12, right: 12, backgroundColor: '#ffffff', flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20, shadowColor: '#000', shadowOpacity: 0.1, shadowRadius: 4, elevation: 3 },
  refreshLocText: { color: '#2563eb', fontWeight: '700', fontSize: 11 },
  punchReviewBlock: { borderWidth: 1, borderColor: '#e2e8f0', borderRadius: 12, padding: 16, marginBottom: 16 },
  punchReviewLabel: { fontSize: 12, fontWeight: '700', color: '#64748b', letterSpacing: 1, marginBottom: 8 },
  punchReviewDataRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  punchReviewVal: { fontSize: 15, fontWeight: '600', color: '#0f172a' },
  editBtnBox: { paddingHorizontal: 12, paddingVertical: 6, backgroundColor: '#f8fafc', borderRadius: 8, borderWidth: 1, borderColor: '#e2e8f0' },
  editBtnBoxText: { color: '#3b82f6', fontWeight: '700', fontSize: 12 },
  editModalLabel: { fontSize: 14, fontWeight: '600', color: '#334155', alignSelf: 'flex-start', marginBottom: 6, marginTop: 4 },
  confirmClockOutBtn: { backgroundColor: '#ef4444', width: '100%', paddingVertical: 14, borderRadius: 16, alignItems: 'center', marginTop: 16 },
  confirmClockOutText: { color: '#ffffff', fontWeight: '800', fontSize: 15 },
  modalInput: { width: '100%', borderWidth: 1, borderColor: '#cbd5e1', borderRadius: 12, padding: 12, marginBottom: 12, fontSize: 14 },
  editedBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: '#fffbeb', borderWidth: 1, borderColor: '#fef3c7', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  editedBadgeText: { color: '#d97706', fontSize: 11, fontWeight: '700' },
  historyLogItem: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 10, borderBottomWidth: 1, borderColor: '#f1f5f9' },
  historyLogText: { fontSize: 13, color: '#334155', flex: 1, fontWeight: '500' }
});
