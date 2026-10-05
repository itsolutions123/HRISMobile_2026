import React, { useState, useEffect, useContext, useCallback, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, Alert, Modal, ScrollView, Animated, TextInput , Platform } from 'react-native';
import DateTimePicker from '@react-native-community/datetimepicker';
import { useFocusEffect } from '@react-navigation/native';
import * as Location from 'expo-location';
import { WebView } from 'react-native-webview';
import { Ionicons } from '@expo/vector-icons';
import * as Notifications from 'expo-notifications';
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
        if (data.is_clocked_in && data.clock_in_time) {
          setClockInTimestampStr(prev => prev || data.clock_in_time);
        } else if (!data.is_clocked_in) {
          setClockInTimestampStr('');
        }
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
      if (res.ok) {
        await fetchStatus();
        try {
          if (!isClockedIn) {
            const { status } = await Notifications.requestPermissionsAsync();
            if (status === 'granted') {
              await Notifications.cancelAllScheduledNotificationsAsync();
              
              const { Platform } = require('react-native');
              if (Platform.OS === 'android') {
                await Notifications.setNotificationChannelAsync('dtr-alerts', {
                  name: 'DTR Alerts',
                  importance: Notifications.AndroidImportance.MAX,
                  vibrationPattern: [0, 250, 250, 250],
                  lightColor: '#FF231F7C',
                });
              }
await Notifications.scheduleNotificationAsync({
                content: {
                  title: 'TIME TO CLOCK OUT!',
                  body: '9hrs 30mins limit reached. Please clock out or check the app.',
                  sound: true,
                  priority: Notifications.AndroidNotificationPriority.MAX,
                },
                trigger: { 
                  seconds: 10,
                  channelId: 'dtr-alerts'
                },
              });
            }
          } else {
            await Notifications.cancelAllScheduledNotificationsAsync();
          }
        } catch (notifErr) {
          console.log('Notification Error', notifErr);
          require('react-native').Alert.alert('Notification Error', notifErr.message || String(notifErr));
        }
      }
    } catch (e) {
      Alert.alert('Connection Error', 'Failed to connect to backend server.');
    }
    setLoading(false);
  };

  const handleSendShiftRevision = (punchType) => {
    const timeVal = punchType === 'CLOCK_IN' ? requestedInTime : requestedOutTime;
    if (!timeVal.trim()) {
      Alert.alert('Missing Field', 'Please select or enter the requested time.');
      return;
    }

    if (punchType === 'CLOCK_IN') {
      setClockInTimestampStr(timeVal);
      setShowEditInModal(false);
    } else {
      setClockOutTimestampStr(timeVal);
      setShowEditOutModal(false);
    }
    
    setIsShiftEdited(true);
    if (editReason.trim()) {
      const newLog = `${punchType}: Edited to ${timeVal} — Reason: ${editReason}`;
      setEditHistoryModalLogs(prev => [newLog, ...prev]);
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
          <View style={[styles.modalSheet, { height: '85%', paddingHorizontal: 20 }]}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Shift ended  <Ionicons name="map-outline" size={20} color="#0f172a" /></Text>
              <TouchableOpacity onPress={() => setShowClockOutReviewModal(false)}>
                <View style={{ backgroundColor: '#ffffff', borderRadius: 20, padding: 4, borderWidth: 1, borderColor: '#e2e8f0' }}>
                  <Ionicons name="close" size={20} color="#475569" />
                </View>
              </TouchableOpacity>
            </View>

            <ScrollView style={{ width: '100%' }} showsVerticalScrollIndicator={false}>
              <Text style={styles.shiftReviewDate}>
                {new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: '2-digit' })}
              </Text>

              <View style={styles.shiftReviewJobPill}>
                <Text style={styles.shiftReviewJobPillText}>{selectedJob?.job_name || 'System Administrator'}</Text>
              </View>

              <View style={styles.timeBoxesContainer}>
                <View style={styles.timeBox}>
                  <Text style={styles.timeBoxTitle}>{clockInTimestampStr || '08:00 AM'}</Text>
                  <View style={styles.timeBoxAddressRow}>
                    <Ionicons name="location-outline" size={12} color="#94a3b8" />
                    <Text style={styles.timeBoxAddressText} numberOfLines={2}>{location?.coords ? `GPS: ${location.coords.latitude.toFixed(4)}, ${location.coords.longitude.toFixed(4)}` : 'Location saved'}</Text>
                  </View>
                </View>

                <Text style={styles.timeArrow}>→</Text>

                <View style={styles.timeBox}>
                  <Text style={styles.timeBoxTitle}>{clockOutTimestampStr || '05:00 PM'}</Text>
                  <View style={styles.timeBoxAddressRow}>
                    <Ionicons name="location-outline" size={12} color="#94a3b8" />
                    <Text style={styles.timeBoxAddressText} numberOfLines={2}>{location?.coords ? `GPS: ${location.coords.latitude.toFixed(4)}, ${location.coords.longitude.toFixed(4)}` : 'Location saved'}</Text>
                  </View>
                </View>
              </View>

              <Text style={styles.totalHoursText}>Total hours {clockInTimestampStr ? '8:00' : '--:--'}</Text>

              <View style={styles.formsContainer}>
                <View style={styles.formRow}>
                  <Ionicons name="create-outline" size={20} color="#3b82f6" />
                  <View style={styles.formRowContent}>
                    <Text style={styles.formRowTitle}>Time In</Text>
                    <Text style={styles.formRowSubtext}>(left blank)</Text>
                  </View>
                </View>
                <View style={styles.formRow}>
                  <Ionicons name="create-outline" size={20} color="#3b82f6" />
                  <View style={styles.formRowContent}>
                    <Text style={styles.formRowTitle}>OB Form</Text>
                    <Text style={styles.formRowSubtext}>(left blank)</Text>
                  </View>
                </View>
                <View style={styles.formRow}>
                  <Ionicons name="create-outline" size={20} color="#3b82f6" />
                  <View style={styles.formRowContent}>
                    <Text style={styles.formRowTitle}>Note</Text>
                    <Text style={styles.formRowSubtext}>(left blank)</Text>
                  </View>
                </View>
              </View>

              <View style={styles.reviewActionRow}>
                <TouchableOpacity style={styles.reviewActionBtnOutline} onPress={() => { setRequestedInTime(clockInTimestampStr); setShowEditInModal(true); }}>
                  <Ionicons name="pencil" size={16} color="#0f172a" />
                  <Text style={styles.reviewActionTextOutline}>Edit</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.reviewActionBtnSolid} onPress={() => submitPunch(selectedJob)} disabled={loading}>
                  {loading ? <ActivityIndicator color="#ffffff" /> : <Text style={styles.reviewActionTextSolid}>Done</Text>}
                </TouchableOpacity>
              </View>
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
  bottomDrawer: { position: 'absolute', bottom: 0, width: '100%', backgroundColor: '#f1f5f9', borderTopLeftRadius: 32, borderTopRightRadius: 32, borderTopWidth: 2, borderTopColor: '#ffffff', borderLeftWidth: 2, borderLeftColor: '#ffffff', paddingBottom: 34, paddingTop: 65, alignItems: 'center', shadowColor: '#94a3b8', shadowOffset: { width: 0, height: -4 }, shadowOpacity: 0.4, shadowRadius: 16, elevation: 16 },
  clockBtnWrapper: { position: 'absolute', top: -75, alignSelf: 'center', backgroundColor: '#f1f5f9', borderRadius: 80, padding: 8, borderTopWidth: 2, borderLeftWidth: 2, borderTopColor: '#ffffff', borderLeftColor: '#ffffff', shadowColor: '#94a3b8', shadowOffset: { width: 8, height: 12 }, shadowOpacity: 0.6, shadowRadius: 16, elevation: 10 },
  bigClockBtn: { width: 130, height: 130, borderRadius: 65, backgroundColor: '#2563eb', alignItems: 'center', justifyContent: 'center', borderTopWidth: 2, borderLeftWidth: 2, borderTopColor: 'rgba(255,255,255,0.4)', borderLeftColor: 'rgba(255,255,255,0.4)' },
  bigClockText: { color: '#ffffff', fontWeight: '800', fontSize: 14, marginTop: 4, letterSpacing: 0.5 },
  quickStatsRow: { flexDirection: 'row', width: '90%', justifyContent: 'space-around', marginTop: 16, backgroundColor: '#f8fafc', padding: 14, borderRadius: 18, alignItems: 'center' },
  statBox: { alignItems: 'center', flex: 1 },
  statDivider: { width: 1, height: 28, backgroundColor: '#e2e8f0' },
  statLabel: { fontSize: 11, color: '#64748b', marginTop: 4 },
  statVal: { fontSize: 12, fontWeight: '700', color: '#0f172a', marginTop: 2 },

  // Shift Active Layout
  activeShiftContainer: { flex: 1, backgroundColor: '#f1f5f9', paddingTop: 24 },
  activeCard: { backgroundColor: '#0f172a', marginHorizontal: 16, borderRadius: 32, paddingVertical: 28, paddingHorizontal: 24, alignItems: 'center', borderTopWidth: 2, borderLeftWidth: 2, borderTopColor: 'rgba(255,255,255,0.15)', borderLeftColor: 'rgba(255,255,255,0.15)', shadowColor: '#94a3b8', shadowOffset: { width: 8, height: 12 }, shadowOpacity: 0.6, shadowRadius: 16, elevation: 10 },
  jobPill: { backgroundColor: 'rgba(255,255,255,0.12)', paddingHorizontal: 16, paddingVertical: 6, borderRadius: 16, marginBottom: 16 },
  jobPillText: { color: '#60a5fa', fontSize: 12, fontWeight: '500' },
  activeTimer: { fontSize: 46, fontWeight: '700', color: '#ffffff', marginBottom: 16, letterSpacing: 1 },
  locRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  locText: { color: '#94a3b8', fontSize: 12 },
  detailsList: { flex: 1, paddingHorizontal: 20, paddingTop: 24 },
  sectionTitle: { fontSize: 16, fontWeight: '600', color: '#0f172a' },
  addNoteBtn: { paddingVertical: 8, marginTop: 4 },
  addNoteText: { fontSize: 15, color: '#334155', fontWeight: '400' },
  contentDivider: { height: 1, backgroundColor: '#cbd5e1', marginVertical: 20 },
  logPlaceholderText: { fontSize: 14, color: '#64748b', fontStyle: 'italic', marginTop: 4 },
  bottomActions: { flexDirection: 'row', paddingHorizontal: 16, paddingTop: 16, paddingBottom: 24, gap: 12, backgroundColor: '#f1f5f9' },
  switchJobBtn: { flex: 1, backgroundColor: '#f1f5f9', height: 54, borderRadius: 24, justifyContent: 'center', alignItems: 'center', flexDirection: 'row', borderTopWidth: 2, borderLeftWidth: 2, borderTopColor: '#ffffff', borderLeftColor: '#ffffff', shadowColor: '#94a3b8', shadowOffset: { width: 4, height: 6 }, shadowOpacity: 0.4, shadowRadius: 8, elevation: 4 },
  switchJobText: { color: '#334155', fontWeight: '800', fontSize: 14 },
  endShiftBtn: { flex: 1.5, backgroundColor: '#ef4444', height: 54, borderRadius: 24, justifyContent: 'center', alignItems: 'center', flexDirection: 'row', borderTopWidth: 2, borderLeftWidth: 2, borderTopColor: 'rgba(255,255,255,0.3)', borderLeftColor: 'rgba(255,255,255,0.3)', shadowColor: '#94a3b8', shadowOffset: { width: 4, height: 6 }, shadowOpacity: 0.4, shadowRadius: 8, elevation: 4 },
  endShiftText: { color: '#ffffff', fontWeight: '800', fontSize: 14 },

  // Fixed Bottom Navigation Tab Bar (Removed)

  // Modal Sheet & Review Modal
  modalBg: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' },
  modalSheet: { backgroundColor: '#f1f5f9', borderTopLeftRadius: 32, borderTopRightRadius: 32, padding: 24, height: '55%', alignItems: 'center', borderTopWidth: 2, borderLeftWidth: 2, borderTopColor: '#ffffff', borderLeftColor: '#ffffff', shadowColor: '#94a3b8', shadowOffset: { width: 0, height: -4 }, shadowOpacity: 0.4, shadowRadius: 16, elevation: 16 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', width: '100%', marginBottom: 16, alignItems: 'center' },
  modalTitle: { fontSize: 18, fontWeight: '700', color: '#0f172a' },
  categoryHeader: { fontSize: 12, fontWeight: '700', color: '#64748b', textTransform: 'uppercase', marginBottom: 12, letterSpacing: 0.5, width: '100%' },
  jobRow: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 16, paddingHorizontal: 16, backgroundColor: '#f1f5f9', borderRadius: 20, marginBottom: 12, width: '100%', justifyContent: 'space-between', borderTopWidth: 2, borderLeftWidth: 2, borderTopColor: '#ffffff', borderLeftColor: '#ffffff', shadowColor: '#94a3b8', shadowOffset: { width: 4, height: 6 }, shadowOpacity: 0.4, shadowRadius: 8, elevation: 4 },
  jobDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: '#2563eb' },
  jobText: { fontSize: 14, color: '#334155', fontWeight: '600', flex: 1 },

  // Shift Review Rework Styles
  shiftReviewDate: { fontSize: 16, fontWeight: '600', color: '#0f172a', marginBottom: 8, alignSelf: 'flex-start' },
  shiftReviewJobPill: { backgroundColor: '#3b82f6', borderRadius: 16, paddingHorizontal: 12, paddingVertical: 4, alignSelf: 'flex-start', marginBottom: 20 },
  shiftReviewJobPillText: { color: '#ffffff', fontSize: 12, fontWeight: '500' },
  timeBoxesContainer: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 },
  timeBox: { flex: 1, backgroundColor: '#f1f5f9', borderRadius: 20, padding: 16, borderTopWidth: 2, borderLeftWidth: 2, borderTopColor: '#ffffff', borderLeftColor: '#ffffff', shadowColor: '#94a3b8', shadowOffset: { width: 4, height: 6 }, shadowOpacity: 0.4, shadowRadius: 8, elevation: 4 },
  timeBoxTitle: { fontSize: 16, fontWeight: '700', color: '#0f172a', marginBottom: 8 },
  timeBoxAddressRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 4 },
  timeBoxAddressText: { fontSize: 11, color: '#64748b', flex: 1 },
  timeArrow: { fontSize: 18, color: '#94a3b8', paddingHorizontal: 8 },
  totalHoursText: { fontSize: 16, fontWeight: '700', color: '#0f172a', alignSelf: 'flex-start', marginBottom: 16 },
  formsContainer: { width: '100%', marginBottom: 24 },
  formRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#e2e8f0' },
  formRowContent: { marginLeft: 12, flex: 1 },
  formRowTitle: { fontSize: 14, color: '#3b82f6', fontWeight: '500' },
  formRowSubtext: { fontSize: 12, color: '#94a3b8' },
  reviewActionRow: { flexDirection: 'row', gap: 12, width: '100%', marginTop: 8 },
  reviewActionBtnOutline: { flex: 1, backgroundColor: '#ffffff', paddingVertical: 14, borderRadius: 24, alignItems: 'center', borderWidth: 1, borderColor: '#e2e8f0', flexDirection: 'row', justifyContent: 'center', gap: 6 },
  reviewActionBtnSolid: { flex: 1, backgroundColor: '#3b82f6', paddingVertical: 14, borderRadius: 24, alignItems: 'center', shadowColor: '#94a3b8', shadowOffset: { width: 4, height: 6 }, shadowOpacity: 0.4, shadowRadius: 8, elevation: 4 },
  reviewActionTextOutline: { color: '#0f172a', fontWeight: '700', fontSize: 15 },
  reviewActionTextSolid: { color: '#ffffff', fontWeight: '700', fontSize: 15 },

  // Original kept for fallback or edit modals
  editModalLabel: { fontSize: 14, fontWeight: '600', color: '#334155', alignSelf: 'flex-start', marginBottom: 6, marginTop: 4 },
  modalInput: { width: '100%', borderWidth: 1, borderColor: '#cbd5e1', borderRadius: 12, padding: 12, marginBottom: 12, fontSize: 14 },
  modalInput: { width: '100%', borderWidth: 1, borderColor: '#cbd5e1', borderRadius: 12, padding: 12, marginBottom: 12, fontSize: 14 },
  editedBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: '#fffbeb', borderWidth: 1, borderColor: '#fef3c7', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  editedBadgeText: { color: '#d97706', fontSize: 11, fontWeight: '700' },
  historyLogItem: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 10, borderBottomWidth: 1, borderColor: '#f1f5f9' },
  historyLogText: { fontSize: 13, color: '#334155', flex: 1, fontWeight: '500' }
});
