import LogoutModal from '../components/LogoutModal';
import React, { useState, useContext } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Alert , Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { AuthContext } from '../context/AuthContext';

export default function ProfileScreen() {
  const [logoutModalVisible, setLogoutModalVisible] = useState(false);
  const { user, logout } = useContext(AuthContext);

  const handleLogout = () => { setLogoutModalVisible(true); };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Top Profile Card */}
      <View style={styles.profileCard}>
        <View style={styles.profileHeader}>
          <View style={styles.logoPlaceholder}>
            <Ionicons name="business" size={28} color="#2563eb" />
          </View>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{user?.name ? user.name.charAt(0).toUpperCase() : 'U'}</Text>
          </View>
        </View>
        <Text style={styles.employeeName}>{user?.name || 'Employee Name'}</Text>
        <Text style={styles.employeeTitle}>{user?.position || 'Staff'} • {user?.department || 'General'}</Text>
      </View>

      {/* Leave Section */}
      <Text style={styles.sectionTitle}>LEAVE</Text>
      <View style={styles.leaveRow}>
        <View style={styles.leaveBox}>
          <Text style={styles.leaveCount}>0</Text>
          <Text style={styles.leaveLabel}>PAID</Text>
        </View>
        <View style={styles.leaveBox}>
          <Text style={styles.leaveCount}>0</Text>
          <Text style={styles.leaveLabel}>VACATION</Text>
        </View>
        <View style={styles.leaveBox}>
          <Text style={styles.leaveCount}>0</Text>
          <Text style={styles.leaveLabel}>OFFSET</Text>
        </View>
      </View>

      {/* Form Submissions */}
      <Text style={styles.sectionTitle}>FORM SUBMISSIONS</Text>
      <View style={styles.listCard}>
        <TouchableOpacity style={styles.listItem} onPress={() => alert('My Submissions coming soon')}>
          <Text style={styles.listItemText}>My Submissions</Text>
          <Ionicons name="chevron-forward" size={20} color="#cbd5e1" />
        </TouchableOpacity>
      </View>

      {/* More Section */}
      <Text style={styles.sectionTitle}>MORE</Text>
      <View style={styles.listCard}>
        <TouchableOpacity style={styles.listItem} onPress={() => alert('Personal Information coming soon')}>
          <Text style={styles.listItemText}>Personal Information</Text>
          <Ionicons name="chevron-forward" size={20} color="#cbd5e1" />
        </TouchableOpacity>
        <TouchableOpacity style={styles.listItem} onPress={() => alert('Settings coming soon')}>
          <Text style={styles.listItemText}>Settings</Text>
          <Ionicons name="chevron-forward" size={20} color="#cbd5e1" />
        </TouchableOpacity>
        <TouchableOpacity style={[styles.listItem, { borderBottomWidth: 0 }]} onPress={() => setLogoutModalVisible(true)}>
          <Text style={[styles.listItemText, { color: '#ef4444' }]}>Logout</Text>
          <Ionicons name="log-out-outline" size={20} color="#ef4444" />
        </TouchableOpacity>
      </View>
      <LogoutModal
          visible={logoutModalVisible}
          onClose={() => setLogoutModalVisible(false)}
          onLogout={() => { setLogoutModalVisible(false); logout(); }}
        />
      </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#eef2f6', paddingTop: Platform.OS === 'ios' ? 60 : 40 },
  content: { padding: 20, paddingTop: 40, paddingBottom: 40 },
  
  clayElement: {
    backgroundColor: '#eef2f6',
    borderRadius: 24,
    shadowColor: '#a3b1c6',
    shadowOffset: { width: 8, height: 8 },
    shadowOpacity: 0.6,
    shadowRadius: 16,
    elevation: 8,
  },

  profileCard: { 
    backgroundColor: '#eef2f6', 
    borderRadius: 24, 
    padding: 24, 
    marginBottom: 32, 
    shadowColor: '#a3b1c6',
    shadowOffset: { width: 8, height: 8 },
    shadowOpacity: 0.6,
    shadowRadius: 16,
    elevation: 8,
  },
  profileHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 },
  
  logoPlaceholder: { 
    width: 50, height: 50, borderRadius: 16, backgroundColor: '#eef2f6', 
    justifyContent: 'center', alignItems: 'center',
    shadowColor: '#a3b1c6', shadowOffset: { width: 4, height: 4 }, shadowOpacity: 0.6, shadowRadius: 8, elevation: 4
  },
  avatar: { 
    width: 64, height: 64, borderRadius: 20, backgroundColor: '#3b82f6', 
    justifyContent: 'center', alignItems: 'center',
    shadowColor: '#3b82f6', shadowOffset: { width: 4, height: 8 }, shadowOpacity: 0.4, shadowRadius: 12, elevation: 6
  },
  avatarText: { color: '#ffffff', fontSize: 28, fontWeight: '800' },
  employeeName: { fontSize: 22, fontWeight: '800', color: '#1e293b', marginBottom: 4 },
  employeeTitle: { fontSize: 13, color: '#64748b', fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5 },

  sectionTitle: { fontSize: 13, fontWeight: '800', color: '#64748b', marginBottom: 16, letterSpacing: 1, paddingLeft: 8 },
  leaveRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 32 },
  
  leaveBox: { 
    flex: 1, backgroundColor: '#eef2f6', borderRadius: 20, paddingVertical: 24, 
    alignItems: 'center', marginHorizontal: 6,
    shadowColor: '#a3b1c6', shadowOffset: { width: 5, height: 5 }, shadowOpacity: 0.5, shadowRadius: 10, elevation: 5
  },
  leaveCount: { fontSize: 28, fontWeight: '800', color: '#3b82f6', marginBottom: 6 },
  leaveLabel: { fontSize: 10, fontWeight: '800', color: '#64748b', textTransform: 'uppercase', letterSpacing: 0.5 },

  listCard: { 
    backgroundColor: '#eef2f6', borderRadius: 24, marginBottom: 32, overflow: 'hidden',
    shadowColor: '#a3b1c6', shadowOffset: { width: 6, height: 6 }, shadowOpacity: 0.5, shadowRadius: 12, elevation: 6
  },
  listItem: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 20, borderBottomWidth: 1, borderBottomColor: '#dde4ee' },
  listItemText: { fontSize: 16, fontWeight: '700', color: '#334155' },
});
