import React, { useState, useEffect, useContext, useCallback, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, ActivityIndicator } from 'react-native';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { AuthContext } from '../context/AuthContext';

export default function HomeScreen() {
  const { user, token, API_BASE_URL } = useContext(AuthContext);
  const navigation = useNavigation();
  const [isClockedIn, setIsClockedIn] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [activeJob, setActiveJob] = useState('');
  const [clockInTime, setClockInTime] = useState('');
  const [fetchingStatus, setFetchingStatus] = useState(true);
  const timerRef = useRef(null);

  const getTimeState = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Morning';
    if (hour < 18) return 'Afternoon';
    return 'Evening';
  };

  const formatTimer = (totalSecs) => {
    const hrs = Math.floor(totalSecs / 3600);
    const mins = Math.floor((totalSecs % 3600) / 60);
    const secs = totalSecs % 60;
    return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  const fetchActiveStatus = useCallback(async () => {
    if (!user || !user.employee_id) return;
    try {
      const response = await fetch(`${API_BASE_URL}/api/punch/active/me`, { headers: { 'Authorization': 'Bearer ' + token } });
      if (response.ok) {
        const data = await response.json();
        setIsClockedIn(data.is_clocked_in);
        if (data.is_clocked_in) {
          setElapsedSeconds(data.elapsed_seconds || 0);
          setActiveJob(data.job_name || 'General Shift');
          
          // Calculate approximate clock in time based on elapsed seconds
          const now = new Date();
          const startTime = new Date(now.getTime() - ((data.elapsed_seconds || 0) * 1000));
          setClockInTime(startTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
        } else {
          setElapsedSeconds(0);
          setActiveJob('');
          setClockInTime('');
        }
      }
    } catch (error) {
      console.log('Error fetching active status:', error);
    } finally {
      setFetchingStatus(false);
    }
  }, [user, API_BASE_URL, token]);

  useFocusEffect(
    useCallback(() => {
      fetchActiveStatus();
      const poller = setInterval(fetchActiveStatus, 5000);
      return () => clearInterval(poller);
    }, [fetchActiveStatus])
  );

  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (isClockedIn) {
      timerRef.current = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isClockedIn]);

  // Mock Feed Data - To be replaced by actual API data when ready
  const mockFeed = [
    { id: 1, date: new Date().toLocaleDateString() + ' 08:00 AM', user: user?.name || 'Employee', event: 'Clocked in to IT Operations' },
    { id: 2, date: 'Yesterday 05:00 PM', user: user?.name || 'Employee', event: 'Clocked out of IT Operations' }
  ];

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
      
      {/* Top Header */}
      <View style={styles.header}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{user?.name ? user.name.charAt(0) : 'U'}</Text>
        </View>
        <Text style={styles.greetingText}>Good {getTimeState()},{'\n'}<Text style={{fontWeight: '800'}}>{user?.name || 'User'}</Text></Text>
      </View>

      {/* Hero Card */}
      <View style={styles.heroCard}>
        {fetchingStatus ? (
          <ActivityIndicator color="#2563eb" size="large" />
        ) : (
          <>
            <Text style={styles.clockTime}>{isClockedIn ? formatTimer(elapsedSeconds) : '00:00:00'}</Text>
            <Text style={styles.clockDetails}>
              {isClockedIn
                ? `${user?.department || 'Dept'} - ${activeJob} | ${clockInTime}`
                : 'NOT CURRENTLY CLOCKED IN'}
            </Text>
          </>
        )}
      </View>

      {/* Action Buttons */}
      <View style={styles.actionRow}>
        <TouchableOpacity style={styles.actionBtn} onPress={() => navigation.navigate('Dashboard')}>
          <Ionicons name="stopwatch-outline" size={26} color="#2563eb" />
          <Text style={styles.actionText}>TIME CLOCK</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.actionBtn} onPress={() => navigation.navigate('Timesheet')}>
          <Ionicons name="calendar-outline" size={26} color="#2563eb" />
          <Text style={styles.actionText}>TIME SHEET</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.actionBtn} onPress={() => alert('Weekly Hours summary coming soon')}>
          <Ionicons name="time-outline" size={26} color="#2563eb" />
          <Text style={styles.actionText}>WEEKLY HOURS</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.divider} />

      {/* Feed Section */}
      <Text style={styles.feedHeader}>FEED</Text>
      {mockFeed.map((item) => (
        <View key={item.id} style={styles.feedCard}>
          <Text style={styles.feedDate}>{item.date}</Text>
          <Text style={styles.feedUser}>{item.user}</Text>
          <Text style={styles.feedEvent}>{item.event}</Text>
          <View style={styles.feedActions}>
            <TouchableOpacity style={styles.feedActionBtn}>
              <Text style={styles.feedActionText}>REACT</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.feedActionBtn}>
              <Text style={styles.feedActionText}>COMMENT</Text>
            </TouchableOpacity>
          </View>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc' },
  content: { padding: 20, paddingTop: 60, paddingBottom: 40 },
  header: { flexDirection: 'row', alignItems: 'center', marginBottom: 24 },
  avatar: { width: 56, height: 56, borderRadius: 28, backgroundColor: '#2563eb', justifyContent: 'center', alignItems: 'center', marginRight: 16 },
  avatarText: { color: '#ffffff', fontSize: 22, fontWeight: '800' },
  greetingText: { fontSize: 18, color: '#0f172a', fontWeight: '500' },
  
  heroCard: { backgroundColor: '#ffffff', borderRadius: 16, padding: 32, alignItems: 'center', marginBottom: 24, borderWidth: 1, borderColor: '#e2e8f0', shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 8, elevation: 4 },
  clockTime: { fontSize: 44, fontWeight: '800', color: '#0f172a', marginBottom: 8, letterSpacing: 1 },
  clockDetails: { fontSize: 11, color: '#64748b', fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5, textAlign: 'center' },
  
  actionRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 24 },
  actionBtn: { flex: 1, backgroundColor: '#ffffff', borderRadius: 16, paddingVertical: 18, alignItems: 'center', borderWidth: 1, borderColor: '#e2e8f0', marginHorizontal: 4, shadowColor: '#000', shadowOpacity: 0.03, shadowRadius: 4, elevation: 2 },
  actionText: { fontSize: 10, fontWeight: '800', color: '#334155', marginTop: 10, textAlign: 'center' },
  
  divider: { height: 1, backgroundColor: '#cbd5e1', marginBottom: 24 },
  
  feedHeader: { fontSize: 24, fontWeight: '800', color: '#0f172a', marginBottom: 16 },
  feedCard: { backgroundColor: '#ffffff', borderRadius: 16, padding: 20, marginBottom: 16, borderWidth: 1, borderColor: '#e2e8f0', shadowColor: '#000', shadowOpacity: 0.03, shadowRadius: 4, elevation: 2 },
  feedDate: { fontSize: 12, fontWeight: '600', color: '#64748b', textAlign: 'center', marginBottom: 10 },
  feedUser: { fontSize: 16, fontWeight: '800', color: '#0f172a', textAlign: 'center', marginBottom: 4 },
  feedEvent: { fontSize: 14, fontWeight: '500', color: '#334155', textAlign: 'center', marginBottom: 20 },
  feedActions: { flexDirection: 'row', justifyContent: 'space-around', borderTopWidth: 1, borderColor: '#f1f5f9', paddingTop: 16 },
  feedActionBtn: { paddingHorizontal: 20, paddingVertical: 4 },
  feedActionText: { fontSize: 12, fontWeight: '700', color: '#64748b' }
});
