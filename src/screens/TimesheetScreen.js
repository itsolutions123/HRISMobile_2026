import React, { useState, useEffect, useContext } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator, Linking, RefreshControl, Platform, Modal, TextInput, Alert } from 'react-native';
import { Calendar } from 'react-native-calendars';
import { Ionicons } from '@expo/vector-icons';
import { AuthContext } from '../context/AuthContext';

export default function TimesheetScreen() {
  const { user, token, API_BASE_URL } = useContext(AuthContext);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [allPunches, setAllPunches] = useState([]);
  const [markedDates, setMarkedDates] = useState({});

  const [showEditModal, setShowEditModal] = useState(false);
  const [editTimeIn, setEditTimeIn] = useState('');
  const [editTimeOut, setEditTimeOut] = useState('');
  const [submittingRevision, setSubmittingRevision] = useState(false);

  const getLocalDateString = (d = new Date()) => {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  const [selectedDate, setSelectedDate] = useState(getLocalDateString());

  const formatCleanTime = (timeStr) => {
    if (!timeStr || timeStr === 'N/A' || timeStr === 'Missing') return 'N/A';
    try {
      if (timeStr.includes('T') || timeStr.includes('-')) {
        const d = new Date(timeStr);
        if (!isNaN(d.getTime())) {
          let hours = d.getHours();
          const minutes = String(d.getMinutes()).padStart(2, '0');
          const ampm = hours >= 12 ? 'PM' : 'AM';
          hours = hours % 12;
          hours = hours ? hours : 12;
          return `${String(hours).padStart(2, '0')}:${minutes} ${ampm}`;
        }
      }
      return timeStr;
    } catch (e) {
      return timeStr;
    }
  };

  const fetchTimesheetData = async () => {
    try {
      const today = new Date();
      const firstDay = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0];
      const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0).toISOString().split('T')[0];

      const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

      const summaryRes = await fetch(`${API_BASE_URL}/api/dtr/summary/${user?.employee_id}?start_date=${firstDay}&end_date=${lastDay}`, { headers });
      if (summaryRes.ok) {
        const data = await summaryRes.json();
        const records = data.daily_details || [];
        let marks = {};
        records.forEach((rec) => {
          if (rec.clock_in || rec.clock_out) {
            marks[rec.date] = { marked: true, dotColor: '#0284c7' };
          }
        });
        marks[selectedDate] = { ...(marks[selectedDate] || {}), selected: true, selectedColor: '#0284c7' };
        setMarkedDates(marks);
      }

      const logsRes = await fetch(`${API_BASE_URL}/api/punch/my-logs`, { headers });
      if (logsRes.ok) {
        const logs = await logsRes.json();
        const userPunches = logs.filter(p => p.employee_id === user?.employee_id);
        setAllPunches(userPunches);
      }
    } catch (error) {
      console.log('Error fetching timesheet:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchTimesheetData();
  }, [selectedDate]);

  const handleDateSelect = (day) => {
    const dateStr = day.dateString;
    setSelectedDate(dateStr);
    let updatedMarks = { ...markedDates };
    Object.keys(updatedMarks).forEach((key) => {
      if (updatedMarks[key].selected) {
        delete updatedMarks[key].selected;
        delete updatedMarks[key].selectedColor;
      }
    });
    updatedMarks[dateStr] = { ...(updatedMarks[dateStr] || {}), selected: true, selectedColor: '#0284c7' };
    setMarkedDates(updatedMarks);
  };

  const normalizeDate = (ts) => {
    if (!ts) return '';
    if (ts.includes('T')) return ts.split('T')[0];
    if (ts.includes(',')) {
      const parts = ts.split(',')[0].split('/');
      if (parts.length === 3) return `${parts[2]}-${parts[0].padStart(2, '0')}-${parts[1].padStart(2, '0')}`;
    }
    const first = ts.split(' ')[0];
    if (first.includes('-')) return first;
    return ts;
  };

  const selectedDayPunches = allPunches.filter(p => normalizeDate(p.timestamp) === selectedDate).sort((a,b) => new Date(a.timestamp) - new Date(b.timestamp));
  const inPunch = selectedDayPunches.find(p => p.punch_type === 'CLOCK_IN');
  const outPunch = [...selectedDayPunches].reverse().find(p => p.punch_type === 'CLOCK_OUT');

  const handleOpenEditShiftModal = () => {
    setEditTimeIn(inPunch ? inPunch.timestamp : `${selectedDate} 08:00:00`);
    setEditTimeOut(outPunch ? outPunch.timestamp : `${selectedDate} 17:00:00`);
    setShowEditModal(true);
  };

  const handleSubmitShiftRevision = async () => {
    if (!editTimeIn.trim() || !editTimeOut.trim()) {
      Alert.alert('Required Fields', 'Please ensure both Clock In and Clock Out times are provided.');
      return;
    }
    setSubmittingRevision(true);
    try {
      const headers = { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) };
      
      const reqIn = fetch(`${API_BASE_URL}/api/manager/revisions/request`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ requested_punch_type: 'CLOCK_IN', requested_timestamp: editTimeIn, reason: 'Bulk shift edit' })
      });

      const reqOut = fetch(`${API_BASE_URL}/api/manager/revisions/request`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ requested_punch_type: 'CLOCK_OUT', requested_timestamp: editTimeOut, reason: 'Bulk shift edit' })
      });

      const [resIn, resOut] = await Promise.all([reqIn, reqOut]);

      if (resIn.ok && resOut.ok) {
        Alert.alert('Revision Submitted', 'Your shift edit request has been sent to your manager.');
        setShowEditModal(false);
        fetchTimesheetData();
      } else {
        Alert.alert('Submission Failed', 'Could not submit one or more shift edit requests.');
      }
    } catch (e) {
      Alert.alert('Error', 'Unable to reach backend server.');
    } finally {
      setSubmittingRevision(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.calendarCardContainer}>
        <Calendar
          current={selectedDate}
          onDayPress={handleDateSelect}
          markedDates={markedDates}
          theme={{
            calendarBackground: '#ffffff', textSectionTitleColor: '#94a3b8',
            selectedDayBackgroundColor: '#0284c7', selectedDayTextColor: '#ffffff',
            todayTextColor: '#0284c7', dayTextColor: '#1e293b',
            textDisabledColor: '#cbd5e1', dotColor: '#0284c7',
            selectedDotColor: '#ffffff', arrowColor: '#0284c7',
            monthTextColor: '#0f172a', indicatorColor: '#0284c7',
            textDayFontWeight: '600', textMonthFontWeight: '700',
            textDayHeaderFontWeight: '600', textDayFontSize: 14,
            textMonthFontSize: 16, textDayHeaderFontSize: 12,
          }}
        />
      </View>

      <ScrollView 
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); fetchTimesheetData(); }} tintColor="#0284c7" />}
        showsVerticalScrollIndicator={false}
      >
        <Text style={styles.summaryTitle}>DTR Logs for {selectedDate}</Text>

        {loading ? (
          <ActivityIndicator size="large" color="#0284c7" style={{ marginTop: 20 }} />
        ) : (inPunch || outPunch) ? (
          <View style={styles.shiftCard}>
            {/* CLOCK IN SECTION */}
            <View style={styles.punchRow}>
              <View style={styles.punchInfo}>
                <Text style={styles.punchType}>CLOCK IN</Text>
                <Text style={styles.punchDetail}>JOB: {user?.job_title || 'N/A'} - {user?.department || 'N/A'}</Text>
                <Text style={styles.punchDetail} numberOfLines={2}>LOCATION TRACKER: {inPunch ? (inPunch.address && inPunch.address !== 'N/A' ? inPunch.address : `${inPunch.latitude}, ${inPunch.longitude}`) : 'Missing'}</Text>
              </View>
              <Text style={styles.punchTime}>{inPunch ? formatCleanTime(inPunch.timestamp) : '--:--'}</Text>
            </View>

            <View style={styles.divider} />

            {/* CLOCK OUT SECTION */}
            <View style={styles.punchRow}>
              <View style={styles.punchInfo}>
                <Text style={styles.punchType}>CLOCK OUT</Text>
                <Text style={styles.punchDetail} numberOfLines={2}>LOCATION TRACKER: {outPunch ? (outPunch.address && outPunch.address !== 'N/A' ? outPunch.address : `${outPunch.latitude}, ${outPunch.longitude}`) : 'Missing'}</Text>
              </View>
              <Text style={styles.punchTime}>{outPunch ? formatCleanTime(outPunch.timestamp) : '--:--'}</Text>
            </View>

            {/* EDIT SHIFT BUTTON */}
            <TouchableOpacity style={styles.editShiftBtn} onPress={handleOpenEditShiftModal}>
              <Text style={styles.editShiftBtnText}>EDIT SHIFT</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <View style={styles.emptyContainer}>
            <Ionicons name="document-text-outline" size={48} color="#cbd5e1" />
            <Text style={styles.emptyText}>No DTR attendance records found.</Text>
          </View>
        )}
      </ScrollView>

      {/* EDIT SHIFT MODAL */}
      <Modal visible={showEditModal} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>SHIFT EDIT</Text>
              <TouchableOpacity onPress={() => setShowEditModal(false)} style={styles.closeBtn}>
                <Ionicons name="close" size={24} color="#64748b" />
              </TouchableOpacity>
            </View>

            <Text style={styles.inputLabel}>CLOCK IN (YYYY-MM-DD HH:MM:SS)</Text>
            <TextInput style={styles.inputField} value={editTimeIn} onChangeText={setEditTimeIn} />

            <Text style={styles.inputLabel}>CLOCK OUT (YYYY-MM-DD HH:MM:SS)</Text>
            <TextInput style={styles.inputField} value={editTimeOut} onChangeText={setEditTimeOut} />

            <TouchableOpacity style={styles.saveBtn} onPress={handleSubmitShiftRevision} disabled={submittingRevision}>
              {submittingRevision ? <ActivityIndicator color="#ffffff" /> : <Text style={styles.saveBtnText}>SAVE SHIFT</Text>}
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#f8fafc' },
  calendarCardContainer: { backgroundColor: '#ffffff', borderRadius: 16, overflow: 'hidden', marginBottom: 16, borderWidth: 1, borderColor: '#f1f5f9', ...Platform.select({ ios: { shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.05, shadowRadius: 8 }, android: { elevation: 3 } }) },
  summaryTitle: { fontSize: 14, fontWeight: '700', color: '#64748b', marginBottom: 12, marginLeft: 4 },
  
  shiftCard: { backgroundColor: '#ffffff', borderRadius: 24, padding: 20, marginBottom: 24, marginHorizontal: 4, borderWidth: 1, borderColor: '#f8fafc', ...Platform.select({ ios: { shadowColor: '#000', shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.08, shadowRadius: 12 }, android: { elevation: 6 } }) },
  punchRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  punchInfo: { flex: 1, paddingRight: 12 },
  punchType: { fontSize: 16, fontWeight: '800', color: '#0f172a', marginBottom: 6 },
  punchDetail: { fontSize: 11, fontWeight: '700', color: '#64748b', marginBottom: 2, textTransform: 'uppercase', lineHeight: 16 },
  punchTime: { fontSize: 16, fontWeight: '800', color: '#0f172a' },
  divider: { height: 1, backgroundColor: '#f1f5f9', marginVertical: 16 },
  
  editShiftBtn: { marginTop: 20, paddingVertical: 14, borderRadius: 16, backgroundColor: '#fef2f2', borderWidth: 1, borderColor: '#fee2e2', alignItems: 'center', ...Platform.select({ ios: { shadowColor: '#ef4444', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.15, shadowRadius: 8 }, android: { elevation: 3 } }) },
  editShiftBtnText: { color: '#ef4444', fontWeight: '800', fontSize: 14, letterSpacing: 0.5 },
  
  emptyContainer: { alignItems: 'center', marginTop: 40, gap: 8 },
  emptyText: { color: '#94a3b8', fontSize: 14, fontWeight: '500' },
  
  modalOverlay: { flex: 1, backgroundColor: 'rgba(15, 23, 42, 0.7)', justifyContent: 'center', alignItems: 'center', padding: 20 },
  modalContent: { backgroundColor: '#ffffff', borderRadius: 24, padding: 24, width: '100%', maxWidth: 360, ...Platform.select({ ios: { shadowColor: '#000', shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.15, shadowRadius: 12 }, android: { elevation: 10 } }) },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  modalTitle: { fontSize: 18, fontWeight: '800', color: '#0f172a' },
  closeBtn: { backgroundColor: '#f1f5f9', padding: 6, borderRadius: 20 },
  inputLabel: { fontSize: 12, fontWeight: '700', color: '#64748b', marginBottom: 8 },
  inputField: { backgroundColor: '#f8fafc', borderWidth: 1, borderColor: '#e2e8f0', borderRadius: 16, padding: 14, marginBottom: 20, fontSize: 14, color: '#0f172a' },
  saveBtn: { backgroundColor: '#0284c7', paddingVertical: 16, borderRadius: 16, alignItems: 'center', marginTop: 10, ...Platform.select({ ios: { shadowColor: '#0284c7', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 8 }, android: { elevation: 4 } }) },
  saveBtnText: { color: '#ffffff', fontWeight: '800', fontSize: 15, letterSpacing: 0.5 }
});
