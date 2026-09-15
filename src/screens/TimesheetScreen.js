import React, { useState, useEffect, useContext } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator, Linking, RefreshControl, Platform, Modal, TextInput, Alert } from 'react-native';
import { Calendar } from 'react-native-calendars';
import { Ionicons } from '@expo/vector-icons';
import { AuthContext } from '../context/AuthContext';

export default function TimesheetScreen() {
  const { user, token, API_BASE_URL } = useContext(AuthContext);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [dailyRecords, setDailyRecords] = useState([]);
  const [allPunches, setAllPunches] = useState([]);
  const [markedDates, setMarkedDates] = useState({});

  // Shift Edit Modal States
  const [showEditModal, setShowEditModal] = useState(false);
  const [editPunchType, setEditPunchType] = useState('CLOCK_IN');
  const [editTimeString, setEditTimeString] = useState('');
  const [editReason, setEditReason] = useState('');
  const [submittingRevision, setSubmittingRevision] = useState(false);

  const getLocalDateString = (d = new Date()) => {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  const [selectedDate, setSelectedDate] = useState(getLocalDateString());

  const formatCleanTime = (timeStr) => {
    if (!timeStr || timeStr === 'N/A' || timeStr === 'Missing' || timeStr === 'Active') return timeStr || 'N/A';
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
        setDailyRecords(records);

        let marks = {};
        records.forEach((rec) => {
          if (rec.clock_in || rec.clock_out) {
            marks[rec.date] = {
              marked: true,
              dotColor: '#0284c7',
            };
          }
        });

        marks[selectedDate] = {
          ...(marks[selectedDate] || {}),
          selected: true,
          selectedColor: '#0284c7',
        };

        setMarkedDates(marks);
      }

      const logsRes = await fetch(`${API_BASE_URL}/api/punch/logs`);
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

    updatedMarks[dateStr] = {
      ...(updatedMarks[dateStr] || {}),
      selected: true,
      selectedColor: '#0284c7',
    };

    setMarkedDates(updatedMarks);
  };

  const openGoogleMaps = (lat, lng) => {
    if (!lat || !lng) return;
    const url = `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`;
    Linking.openURL(url);
  };

  const handleOpenEditShiftModal = () => {
    const now = new Date();
    const formatted = `${selectedDate} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:00`;
    setEditTimeString(formatted);
    setEditReason('');
    setShowEditModal(true);
  };

  const handleSubmitShiftRevision = async () => {
    if (!editTimeString.trim() || !editReason.trim()) {
      Alert.alert('Required Fields', 'Please enter the requested timestamp and reason.');
      return;
    }

    setSubmittingRevision(true);
    try {
      const headers = {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      };
      const res = await fetch(`${API_BASE_URL}/api/manager/revisions/request`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          requested_punch_type: editPunchType,
          requested_timestamp: editTimeString,
          reason: editReason
        })
      });

      if (res.ok) {
        Alert.alert('Revision Submitted', 'Your shift edit request has been sent to your manager for approval.');
        setShowEditModal(false);
        fetchTimesheetData();
      } else {
        const err = await res.json();
        Alert.alert('Submission Failed', err.detail || 'Could not submit shift edit request.');
      }
    } catch (e) {
      Alert.alert('Error', 'Unable to reach backend server.');
    } finally {
      setSubmittingRevision(false);
    }
  };

  const selectedDayRecord = dailyRecords.find(r => r.date === selectedDate);
  const selectedDayPunches = allPunches.filter(p => {
    const pDate = (p.timestamp || '').split('T')[0] || (p.timestamp || '').split(' ')[0];
    return pDate === selectedDate;
  });

  return (
    <View style={styles.container}>
      {/* CALENDAR WIDGET */}
      <View style={styles.calendarCardContainer}>
        <Calendar
          current={selectedDate}
          onDayPress={handleDateSelect}
          markedDates={markedDates}
          theme={{
            calendarBackground: '#ffffff',
            textSectionTitleColor: '#94a3b8',
            selectedDayBackgroundColor: '#0284c7',
            selectedDayTextColor: '#ffffff',
            todayTextColor: '#0284c7',
            dayTextColor: '#1e293b',
            textDisabledColor: '#cbd5e1',
            dotColor: '#0284c7',
            selectedDotColor: '#ffffff',
            arrowColor: '#0284c7',
            monthTextColor: '#0f172a',
            indicatorColor: '#0284c7',
            textDayFontWeight: '600',
            textMonthFontWeight: '700',
            textDayHeaderFontWeight: '600',
            textDayFontSize: 14,
            textMonthFontSize: 16,
            textDayHeaderFontSize: 12,
          }}
        />
      </View>

      {/* SUMMARY HEADER BAR */}
      <View style={styles.summaryBar}>
        <View style={styles.summaryLeft}>
          <Ionicons name="calendar-outline" size={18} color="#0284c7" />
          <Text style={styles.summaryTitle}>
            DTR Details for {selectedDate}
          </Text>
        </View>
        <View style={styles.durationPill}>
          <Ionicons name="time-outline" size={13} color="#ffffff" style={{ marginRight: 4 }} />
          <Text style={styles.durationText}>
            {selectedDayRecord ? `${selectedDayRecord.regular_hours} hrs` : '0 hrs'}
          </Text>
        </View>
      </View>

      {/* CLEAN DAILY DTR CARD */}
      {selectedDayRecord && (selectedDayRecord.clock_in || selectedDayRecord.clock_out) ? (
        <View style={styles.dtrSummaryCard}>
          <View style={styles.dtrSummaryRow}>
            <Text style={styles.dtrLabel}>Shift In / Out:</Text>
            <Text style={styles.dtrValue}>
              {formatCleanTime(selectedDayRecord.clock_in)} - {formatCleanTime(selectedDayRecord.clock_out)}
            </Text>
          </View>
          <View style={styles.dtrSummaryRow}>
            <Text style={styles.dtrLabel}>Late / Undertime:</Text>
            <Text style={[styles.dtrValue, { color: '#ef4444' }]}>
              {selectedDayRecord.late_minutes}m late / {selectedDayRecord.undertime_minutes}m undertime
            </Text>
          </View>
          <TouchableOpacity style={styles.editShiftBtn} onPress={handleOpenEditShiftModal}>
            <Ionicons name="create-outline" size={15} color="#0284c7" />
            <Text style={styles.editShiftBtnText}>Edit Shift (Request Revision)</Text>
          </TouchableOpacity>
        </View>
      ) : null}

      {/* PUNCH FEED LIST */}
      {loading ? (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color="#0284c7" />
        </View>
      ) : selectedDayPunches.length > 0 ? (
        <FlatList
          data={selectedDayPunches}
          keyExtractor={(item) => (item.id ? item.id.toString() : Math.random().toString())}
          contentContainerStyle={{ paddingBottom: 20 }}
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); fetchTimesheetData(); }} tintColor="#0284c7" />
          }
          renderItem={({ item }) => {
            const isClockIn = item.punch_type === 'CLOCK_IN';
            return (
              <View style={styles.punchCard}>
                <View style={styles.cardTopRow}>
                  <View style={[styles.statusBadge, isClockIn ? styles.badgeIn : styles.badgeOut]}>
                    <Ionicons
                      name={isClockIn ? "arrow-down-circle-outline" : "arrow-up-circle-outline"}
                      size={14}
                      color={isClockIn ? "#166534" : "#991b1b"}
                    />
                    <Text style={[styles.statusBadgeText, isClockIn ? styles.textIn : styles.textOut]}>
                      {isClockIn ? 'CLOCK IN' : 'CLOCK OUT'}
                    </Text>
                  </View>

                  <Text style={styles.timestampText}>{formatCleanTime(item.timestamp)}</Text>
                </View>

                <View style={styles.locationRow}>
                  <Ionicons name="location-sharp" size={15} color="#64748b" style={{ marginRight: 4 }} />
                  <Text style={styles.addressText} numberOfLines={1}>{item.address || 'Duty Shift'}</Text>
                </View>

                {item.latitude && item.longitude ? (
                  <TouchableOpacity
                    style={styles.mapActionChip}
                    activeOpacity={0.7}
                    onPress={() => openGoogleMaps(item.latitude, item.longitude)}
                  >
                    <Ionicons name="map-outline" size={14} color="#0284c7" />
                    <Text style={styles.mapActionText}>View Location Pin</Text>
                  </TouchableOpacity>
                ) : null}
              </View>
            );
          }}
        />
      ) : (
        <View style={styles.emptyContainer}>
          <Ionicons name="document-text-outline" size={48} color="#cbd5e1" />
          <Text style={styles.emptyText}>No DTR attendance records found for {selectedDate}.</Text>
        </View>
      )}

      {/* EDIT SHIFT MODAL */}
      <Modal visible={showEditModal} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Request Shift Edit</Text>
              <TouchableOpacity onPress={() => setShowEditModal(false)}>
                <Ionicons name="close" size={24} color="#64748b" />
              </TouchableOpacity>
            </View>

            <Text style={{ fontSize: 12, fontWeight: '700', color: '#64748b', marginBottom: 6 }}>PUNCH TYPE</Text>
            <View style={{ flexDirection: 'row', gap: 8, marginBottom: 14 }}>
              <TouchableOpacity
                style={{ flex: 1, paddingVertical: 10, borderRadius: 10, borderWidth: 1, borderColor: editPunchType === 'CLOCK_IN' ? '#0284c7' : '#cbd5e1', backgroundColor: editPunchType === 'CLOCK_IN' ? '#eff6ff' : '#ffffff', alignItems: 'center' }}
                onPress={() => setEditPunchType('CLOCK_IN')}
              >
                <Text style={{ fontSize: 13, fontWeight: '700', color: editPunchType === 'CLOCK_IN' ? '#0284c7' : '#475569' }}>CLOCK IN</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={{ flex: 1, paddingVertical: 10, borderRadius: 10, borderWidth: 1, borderColor: editPunchType === 'CLOCK_OUT' ? '#0284c7' : '#cbd5e1', backgroundColor: editPunchType === 'CLOCK_OUT' ? '#eff6ff' : '#ffffff', alignItems: 'center' }}
                onPress={() => setEditPunchType('CLOCK_OUT')}
              >
                <Text style={{ fontSize: 13, fontWeight: '700', color: editPunchType === 'CLOCK_OUT' ? '#0284c7' : '#475569' }}>CLOCK OUT</Text>
              </TouchableOpacity>
            </View>

            <Text style={{ fontSize: 12, fontWeight: '700', color: '#64748b', marginBottom: 6 }}>REQUESTED TIMESTAMP (YYYY-MM-DD HH:MM:SS)</Text>
            <TextInput
              style={{ borderWidth: 1, borderColor: '#cbd5e1', borderRadius: 10, padding: 12, marginBottom: 14, fontSize: 14 }}
              value={editTimeString}
              onChangeText={setEditTimeString}
            />

            <Text style={{ fontSize: 12, fontWeight: '700', color: '#64748b', marginBottom: 6 }}>REASON FOR EDIT</Text>
            <TextInput
              style={{ borderWidth: 1, borderColor: '#cbd5e1', borderRadius: 10, padding: 12, marginBottom: 18, fontSize: 14, height: 75 }}
              placeholder="Explain why shift edit is required..."
              multiline
              value={editReason}
              onChangeText={setEditReason}
            />

            <TouchableOpacity
              style={{ backgroundColor: '#0284c7', paddingVertical: 14, borderRadius: 12, alignItems: 'center' }}
              onPress={handleSubmitShiftRevision}
              disabled={submittingRevision}
            >
              {submittingRevision ? (
                <ActivityIndicator color="#ffffff" />
              ) : (
                <Text style={{ color: '#ffffff', fontWeight: '800', fontSize: 15 }}>Send to Manager for Approval</Text>
              )}
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#f8fafc' },
  calendarCardContainer: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    overflow: 'hidden',
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#f1f5f9',
    ...Platform.select({
      ios: { shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.05, shadowRadius: 8 },
      android: { elevation: 3 },
    }),
  },
  summaryBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
    paddingHorizontal: 4,
  },
  summaryLeft: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  summaryTitle: { fontSize: 15, fontWeight: '700', color: '#0f172a' },
  durationPill: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0284c7',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 20,
  },
  durationText: { color: '#ffffff', fontWeight: '700', fontSize: 12 },
  dtrSummaryCard: {
    backgroundColor: '#ffffff',
    borderRadius: 14,
    padding: 14,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  dtrSummaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  dtrLabel: { fontSize: 13, color: '#64748b', fontWeight: '600' },
  dtrValue: { fontSize: 13, color: '#0f172a', fontWeight: '700' },
  editShiftBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    backgroundColor: '#eff6ff',
    borderColor: '#bfdbfe',
    borderWidth: 1,
    paddingVertical: 10,
    borderRadius: 10,
    marginTop: 8,
  },
  editShiftBtnText: { color: '#0284c7', fontWeight: '800', fontSize: 13 },
  punchCard: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#f1f5f9',
    ...Platform.select({
      ios: { shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.04, shadowRadius: 4 },
      android: { elevation: 2 },
    }),
  },
  cardTopRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  badgeIn: { backgroundColor: '#f0fdf4', borderWidth: 1, borderColor: '#bbf7d0' },
  badgeOut: { backgroundColor: '#fef2f2', borderWidth: 1, borderColor: '#fecaca' },
  statusBadgeText: { fontWeight: '700', fontSize: 11, letterSpacing: 0.3 },
  textIn: { color: '#166534' },
  textOut: { color: '#991b1b' },
  timestampText: { fontSize: 13, fontWeight: '700', color: '#334155' },
  locationRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  addressText: { fontSize: 13, color: '#64748b', flex: 1 },
  mapActionChip: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    backgroundColor: '#eff6ff',
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#dbeafe',
  },
  mapActionText: { color: '#0284c7', fontWeight: '600', fontSize: 12 },
  centerContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  emptyContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', marginTop: 30, gap: 8 },
  emptyText: { color: '#94a3b8', fontSize: 14, fontWeight: '500' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(15, 23, 42, 0.7)', justifyContent: 'center', padding: 20 },
  modalContent: { backgroundColor: '#ffffff', borderRadius: 24, padding: 22 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  modalTitle: { fontSize: 18, fontWeight: '800', color: '#0f172a' },
});
