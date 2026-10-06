import React, { useState, useEffect, useContext } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator, RefreshControl, Platform, Modal, TextInput, Alert } from 'react-native';
import { Calendar } from 'react-native-calendars';
import { Ionicons } from '@expo/vector-icons';
import { AuthContext } from '../context/AuthContext';

export default function TimesheetScreen() {
  const { user, token, API_BASE_URL } = useContext(AuthContext);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [allPunches, setAllPunches] = useState([]);
  const [markedDates, setMarkedDates] = useState({});

  // Dynamic Jobs for Employee's Smart Group / Department
  const [smartGroupName, setSmartGroupName] = useState('');
  const [availableJobs, setAvailableJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState('');

  // Structured Time Picker State (Hours, Minutes, AM/PM)
  const [startHour, setStartHour] = useState('09');
  const [startMin, setStartMin] = useState('00');
  const [startAmpm, setStartAmpm] = useState('AM');

  const [endHour, setEndHour] = useState('05');
  const [endMin, setEndMin] = useState('00');
  const [endAmpm, setEndAmpm] = useState('PM');

  const [timePickerTarget, setTimePickerTarget] = useState(null); // 'START' or 'END'
  const [showTimePickerModal, setShowTimePickerModal] = useState(false);

  // Modal Note & Submission State
  const [showEditModal, setShowEditModal] = useState(false);
  const [editNote, setEditNote] = useState('');
  const [submittingRevision, setSubmittingRevision] = useState(false);

  const getLocalDateString = (d = new Date()) => {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  const [selectedDate, setSelectedDate] = useState(getLocalDateString());

  // Format date for modal header display (e.g. October 5th 2026)
  const formatDisplayDate = (dateStr) => {
    if (!dateStr) return '';
    try {
      const parts = dateStr.split('-');
      if (parts.length === 3) {
        const d = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
        const monthName = d.toLocaleString('en-US', { month: 'long' });
        const dayNum = d.getDate();
        let suffix = 'th';
        if (dayNum % 10 === 1 && dayNum !== 11) suffix = 'st';
        else if (dayNum % 10 === 2 && dayNum !== 12) suffix = 'nd';
        else if (dayNum % 10 === 3 && dayNum !== 13) suffix = 'rd';
        return `${monthName} ${dayNum}${suffix} ${parts[0]}`;
      }
      return dateStr;
    } catch (e) {
      return dateStr;
    }
  };

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

  // Parse raw timestamp into structured hours, minutes, and ampm
  const parseTimestampToParts = (ts, defaultH, defaultM, defaultAmpm) => {
    if (!ts) return { h: defaultH, m: defaultM, ampm: defaultAmpm };
    try {
      const d = new Date(ts.includes('T') || ts.includes('-') ? ts : `${selectedDate}T${ts}`);
      if (isNaN(d.getTime())) return { h: defaultH, m: defaultM, ampm: defaultAmpm };
      let hours = d.getHours();
      const mins = String(d.getMinutes()).padStart(2, '0');
      const ampm = hours >= 12 ? 'PM' : 'AM';
      hours = hours % 12;
      hours = hours ? hours : 12;
      return { h: String(hours).padStart(2, '0'), m: mins, ampm };
    } catch (e) {
      return { h: defaultH, m: defaultM, ampm: defaultAmpm };
    }
  };

  const calculateTotalHours = () => {
    try {
      let h1 = parseInt(startHour, 10) || 0;
      let m1 = parseInt(startMin, 10) || 0;
      if (startAmpm === 'PM' && h1 < 12) h1 += 12;
      if (startAmpm === 'AM' && h1 === 12) h1 = 0;

      let h2 = parseInt(endHour, 10) || 0;
      let m2 = parseInt(endMin, 10) || 0;
      if (endAmpm === 'PM' && h2 < 12) h2 += 12;
      if (endAmpm === 'AM' && h2 === 12) h2 = 0;

      const d1 = new Date(selectedDate);
      d1.setHours(h1, m1, 0, 0);

      const d2 = new Date(selectedDate);
      d2.setHours(h2, m2, 0, 0);

      const diffMs = d2 - d1;
      if (diffMs <= 0) return '0:00';
      const totalMins = Math.floor(diffMs / (1000 * 60));
      const hrs = Math.floor(totalMins / 60);
      const mins = totalMins % 60;
      return `${hrs}:${String(mins).padStart(2, '0')}`;
    } catch (e) {
      return '8:00';
    }
  };

  // Fetch smart groups & job titles dynamically from backend
  const fetchSmartGroupsAndJobs = async () => {
    try {
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

      // 1. Fetch employee's assigned smart group / department
      const userGroup = user?.smart_group || user?.department || '';
      setSmartGroupName(userGroup || 'General');

      // 2. Fetch jobs catalog
      const jobsRes = await fetch(`${API_BASE_URL}/api/jobs`, { headers });
      if (jobsRes.ok) {
        const categories = await jobsRes.json();
        let matchedTitles = [];

        // Find matching job category/group
        const groupMatch = categories.find(c =>
          c.name?.toLowerCase() === userGroup.toLowerCase() ||
          c.code?.toLowerCase() === userGroup.toLowerCase() ||
          c.description?.toLowerCase() === userGroup.toLowerCase()
        );

        if (groupMatch && groupMatch.sub_items && groupMatch.sub_items.length > 0) {
          matchedTitles = groupMatch.sub_items.map(s => s.name);
        } else if (categories.length > 0 && categories[0].sub_items) {
          // Fallback to first category sub_items if exact group match has no sub_items
          matchedTitles = categories[0].sub_items.map(s => s.name);
        }

        if (matchedTitles.length > 0) {
          setAvailableJobs(matchedTitles);
          if (!selectedJob || !matchedTitles.includes(selectedJob)) {
            setSelectedJob(user?.job_title || matchedTitles[0]);
          }
        } else {
          setAvailableJobs(user?.job_title ? [user.job_title] : []);
        }
      }
    } catch (e) {
      console.log('Error fetching smart groups/jobs:', e);
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
    fetchSmartGroupsAndJobs();
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
    const startParts = parseTimestampToParts(inPunch ? inPunch.timestamp : null, '09', '00', 'AM');
    setStartHour(startParts.h);
    setStartMin(startParts.m);
    setStartAmpm(startParts.ampm);

    const endParts = parseTimestampToParts(outPunch ? outPunch.timestamp : null, '05', '00', 'PM');
    setEndHour(endParts.h);
    setEndMin(endParts.m);
    setEndAmpm(endParts.ampm);

    setEditNote('');
    setShowEditModal(true);
  };

  const handleSubmitShiftRevision = async () => {
    let h1 = parseInt(startHour, 10) || 0;
    let m1 = parseInt(startMin, 10) || 0;
    if (startAmpm === 'PM' && h1 < 12) h1 += 12;
    if (startAmpm === 'AM' && h1 === 12) h1 = 0;

    let h2 = parseInt(endHour, 10) || 0;
    let m2 = parseInt(endMin, 10) || 0;
    if (endAmpm === 'PM' && h2 < 12) h2 += 12;
    if (endAmpm === 'AM' && h2 === 12) h2 = 0;

    const formattedStartISO = `${selectedDate} ${String(h1).padStart(2, '0')}:${String(m1).padStart(2, '0')}:00`;
    const formattedEndISO = `${selectedDate} ${String(h2).padStart(2, '0')}:${String(m2).padStart(2, '0')}:00`;

    setSubmittingRevision(true);
    try {
      const headers = { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) };
      const reasonText = editNote.trim() ? `[Job: ${selectedJob}] ${editNote.trim()}` : `Shift edit request [Job: ${selectedJob}]`;

      const reqIn = fetch(`${API_BASE_URL}/api/manager/revisions/request`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ requested_punch_type: 'CLOCK_IN', requested_timestamp: formattedStartISO, reason: reasonText })
      });

      const reqOut = fetch(`${API_BASE_URL}/api/manager/revisions/request`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ requested_punch_type: 'CLOCK_OUT', requested_timestamp: formattedEndISO, reason: reasonText })
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

  const hoursList = ['01','02','03','04','05','06','07','08','09','10','11','12'];
  const minsList = ['00','15','30','45','58','20'];

  const openPicker = (target) => {
    setTimePickerTarget(target);
    setShowTimePickerModal(true);
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

      {/* EDIT SHIFT CLAY MODAL */}
      <Modal visible={showEditModal} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.clayModalContainer}>
            {/* Header */}
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Add shift</Text>
              <TouchableOpacity onPress={() => setShowEditModal(false)} style={styles.closeBtnPill}>
                <Ionicons name="close" size={20} color="#64748b" />
              </TouchableOpacity>
            </View>

            <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: 10 }}>
              {/* Job Row */}
              <View style={styles.clayRow}>
                <Text style={styles.rowLabel}>Job</Text>
                <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.jobPillsContainer}>
                  {smartGroupName ? (
                    <View style={styles.clayGroupTag}>
                      <Text style={styles.clayGroupText}>{smartGroupName}</Text>
                    </View>
                  ) : null}
                  {availableJobs.map((jobName, idx) => {
                    const isSelected = selectedJob === jobName;
                    return (
                      <TouchableOpacity
                        key={idx}
                        style={[styles.clayPillTag, isSelected && styles.clayPillTagSelected]}
                        onPress={() => setSelectedJob(jobName)}
                        activeOpacity={0.7}
                      >
                        <Text style={[styles.clayPillText, isSelected && styles.clayPillTextSelected]}>{jobName}</Text>
                      </TouchableOpacity>
                    );
                  })}
                </ScrollView>
              </View>

              {/* Starts Row */}
              <View style={styles.clayRow}>
                <Text style={styles.rowLabel}>Starts</Text>
                <View style={styles.timeRowRight}>
                  <Text style={styles.fixedDateText}>{formatDisplayDate(selectedDate)}</Text>
                  <TouchableOpacity style={styles.clayTimePickerPill} onPress={() => openPicker('START')}>
                    <Text style={styles.clayTimePickerText}>{`${startHour}:${startMin} ${startAmpm}`}</Text>
                  </TouchableOpacity>
                </View>
              </View>

              {/* Ends Row */}
              <View style={styles.clayRow}>
                <Text style={styles.rowLabel}>Ends</Text>
                <View style={styles.timeRowRight}>
                  <Text style={styles.fixedDateText}>{formatDisplayDate(selectedDate)}</Text>
                  <TouchableOpacity style={styles.clayTimePickerPill} onPress={() => openPicker('END')}>
                    <Text style={styles.clayTimePickerText}>{`${endHour}:${endMin} ${endAmpm}`}</Text>
                  </TouchableOpacity>
                </View>
              </View>

              {/* Total Hours */}
              <View style={styles.totalHoursRow}>
                <Text style={styles.totalHoursText}>
                  Total hours <Text style={styles.totalHoursValue}>{calculateTotalHours()}</Text>
                </Text>
              </View>

              {/* Note / Reason Section */}
              <View style={styles.noteHeaderRow}>
                <Ionicons name="create-outline" size={18} color="#0284c7" />
                <Text style={styles.noteHeaderTitle}>Add a note</Text>
              </View>

              <TextInput
                style={styles.clayTextArea}
                value={editNote}
                onChangeText={setEditNote}
                placeholder="Attach a note to your request"
                placeholderTextColor="#94a3b8"
                multiline
                numberOfLines={3}
              />

              <Text style={styles.disclaimerText}>All requests will be sent for a manager's approval</Text>

              {/* Action Button */}
              <TouchableOpacity
                style={styles.claySubmitBtn}
                onPress={handleSubmitShiftRevision}
                disabled={submittingRevision}
                activeOpacity={0.8}
              >
                {submittingRevision ? (
                  <ActivityIndicator color="#ffffff" />
                ) : (
                  <Text style={styles.claySubmitBtnText}>Send for approval</Text>
                )}
              </TouchableOpacity>
            </ScrollView>
          </View>
        </View>
      </Modal>

      {/* CONSTRAINED TIME PICKER MODAL */}
      <Modal visible={showTimePickerModal} transparent animationType="fade">
        <View style={styles.pickerOverlay}>
          <View style={styles.pickerCard}>
            <Text style={styles.pickerTitle}>Set {timePickerTarget === 'START' ? 'Start' : 'End'} Time</Text>

            <View style={styles.pickerSelectorsRow}>
              {/* Hours */}
              <ScrollView style={styles.pickerCol} showsVerticalScrollIndicator={false}>
                {hoursList.map(h => {
                  const curr = timePickerTarget === 'START' ? startHour : endHour;
                  const active = curr === h;
                  return (
                    <TouchableOpacity
                      key={h}
                      style={[styles.pickerItem, active && styles.pickerItemActive]}
                      onPress={() => timePickerTarget === 'START' ? setStartHour(h) : setEndHour(h)}
                    >
                      <Text style={[styles.pickerItemText, active && styles.pickerItemTextActive]}>{h}</Text>
                    </TouchableOpacity>
                  );
                })}
              </ScrollView>

              <Text style={styles.colonSeparator}>:</Text>

              {/* Minutes */}
              <ScrollView style={styles.pickerCol} showsVerticalScrollIndicator={false}>
                {minsList.map(m => {
                  const curr = timePickerTarget === 'START' ? startMin : endMin;
                  const active = curr === m;
                  return (
                    <TouchableOpacity
                      key={m}
                      style={[styles.pickerItem, active && styles.pickerItemActive]}
                      onPress={() => timePickerTarget === 'START' ? setStartMin(m) : setEndMin(m)}
                    >
                      <Text style={[styles.pickerItemText, active && styles.pickerItemTextActive]}>{m}</Text>
                    </TouchableOpacity>
                  );
                })}
              </ScrollView>

              {/* AM / PM */}
              <View style={styles.pickerCol}>
                {['AM', 'PM'].map(p => {
                  const curr = timePickerTarget === 'START' ? startAmpm : endAmpm;
                  const active = curr === p;
                  return (
                    <TouchableOpacity
                      key={p}
                      style={[styles.pickerItem, active && styles.pickerItemActive]}
                      onPress={() => timePickerTarget === 'START' ? setStartAmpm(p) : setEndAmpm(p)}
                    >
                      <Text style={[styles.pickerItemText, active && styles.pickerItemTextActive]}>{p}</Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
            </View>

            <TouchableOpacity style={styles.pickerDoneBtn} onPress={() => setShowTimePickerModal(false)}>
              <Text style={styles.pickerDoneText}>Done</Text>
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

  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(15, 23, 42, 0.4)',
    justifyContent: 'flex-end',
    alignItems: 'center',
  },
  clayModalContainer: {
    width: '100%',
    maxHeight: '88%',
    backgroundColor: '#ffffff',
    borderTopLeftRadius: 32,
    borderTopRightRadius: 32,
    paddingTop: 24,
    paddingHorizontal: 22,
    paddingBottom: Platform.OS === 'ios' ? 36 : 24,
    borderTopWidth: 2,
    borderLeftWidth: 2,
    borderTopColor: '#ffffff',
    borderLeftColor: '#ffffff',
    shadowColor: '#64748b',
    shadowOffset: { width: 0, height: -8 },
    shadowOpacity: 0.25,
    shadowRadius: 16,
    elevation: 12,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  modalTitle: {
    fontSize: 22,
    fontWeight: '700',
    color: '#0f172a',
  },
  closeBtnPill: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#f8fafc',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  clayRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#f1f5f9',
  },
  rowLabel: {
    fontSize: 15,
    fontWeight: '500',
    color: '#334155',
    width: 55,
  },
  jobPillsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  clayGroupTag: {
    backgroundColor: '#dbeafe',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  clayGroupText: {
    color: '#1d4ed8',
    fontSize: 13,
    fontWeight: '600',
  },
  clayPillTag: {
    backgroundColor: '#e0e7ff',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#c7d2fe',
  },
  clayPillTagSelected: {
    backgroundColor: '#3b82f6',
    borderColor: '#2563eb',
  },
  clayPillText: {
    color: '#4338ca',
    fontSize: 13,
    fontWeight: '600',
  },
  clayPillTextSelected: {
    color: '#ffffff',
  },
  timeRowRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  fixedDateText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#0284c7',
  },
  clayTimePickerPill: {
    backgroundColor: '#e0f2fe',
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderWidth: 1,
    borderColor: '#bae6fd',
  },
  clayTimePickerText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0284c7',
  },
  totalHoursRow: {
    marginVertical: 18,
  },
  totalHoursText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#0f172a',
  },
  totalHoursValue: {
    fontWeight: '800',
    color: '#0f172a',
  },
  noteHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 8,
  },
  noteHeaderTitle: {
    fontSize: 14,
    fontWeight: '500',
    color: '#334155',
  },
  clayTextArea: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    padding: 14,
    fontSize: 14,
    color: '#0f172a',
    borderWidth: 1,
    borderColor: '#e2e8f0',
    minHeight: 80,
    textAlignVertical: 'top',
    marginBottom: 12,
  },
  disclaimerText: {
    fontSize: 12,
    color: '#94a3b8',
    textAlign: 'center',
    marginBottom: 20,
  },
  claySubmitBtn: {
    backgroundColor: '#2563eb',
    borderRadius: 28,
    paddingVertical: 16,
    alignItems: 'center',
    shadowColor: '#2563eb',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  claySubmitBtnText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },

  /* Time Picker Card Styles */
  pickerOverlay: {
    flex: 1,
    backgroundColor: 'rgba(15, 23, 42, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  pickerCard: {
    width: '80%',
    maxWidth: 320,
    backgroundColor: '#ffffff',
    borderRadius: 24,
    padding: 20,
    alignItems: 'center',
    elevation: 8,
  },
  pickerTitle: {
    fontSize: 17,
    fontWeight: '700',
    color: '#0f172a',
    marginBottom: 16,
  },
  pickerSelectorsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justify: 'center',
    height: 140,
    gap: 12,
    marginBottom: 16,
  },
  pickerCol: {
    width: 60,
  },
  colonSeparator: {
    fontSize: 20,
    fontWeight: '700',
    color: '#0f172a',
  },
  pickerItem: {
    paddingVertical: 8,
    alignItems: 'center',
    borderRadius: 8,
    marginVertical: 2,
  },
  pickerItemActive: {
    backgroundColor: '#0284c7',
  },
  pickerItemText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#475569',
  },
  pickerItemTextActive: {
    color: '#ffffff',
    fontWeight: '700',
  },
  pickerDoneBtn: {
    backgroundColor: '#0284c7',
    paddingVertical: 10,
    paddingHorizontal: 28,
    borderRadius: 16,
  },
  pickerDoneText: {
    color: '#ffffff',
    fontWeight: '700',
    fontSize: 15,
  },
});
