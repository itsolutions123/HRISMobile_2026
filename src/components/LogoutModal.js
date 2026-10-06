import React from 'react';
import { Modal, View, Text, TouchableOpacity, Pressable, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export default function LogoutModal({ visible, onClose, onLogout }) {
  return (
    <Modal
      visible={visible}
      transparent={true}
      animationType="fade"
      onRequestClose={onClose}
    >
      <Pressable style={styles.backdrop} onPress={onClose}>
        <Pressable style={styles.clayCard} onPress={(e) => e.stopPropagation()}>
          <View style={styles.iconBadge}>
            <Ionicons name="log-out-outline" size={32} color="#dc2626" />
          </View>
          <Text style={styles.title}>Logout Confirmation</Text>
          <Text style={styles.message}>Are you sure you want to log out of atWork?</Text>
          <View style={styles.buttonRow}>
            <TouchableOpacity style={styles.cancelBtn} onPress={onClose}>
              <Text style={styles.cancelText}>Cancel</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.logoutBtn} onPress={onLogout}>
              <Text style={styles.logoutText}>Logout</Text>
            </TouchableOpacity>
          </View>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(15, 23, 42, 0.65)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20
  },
  clayCard: {
    width: '100%',
    maxWidth: 340,
    backgroundColor: '#eef2f6',
    borderRadius: 32,
    padding: 28,
    alignItems: 'center',
    borderTopWidth: 2,
    borderLeftWidth: 2,
    borderTopColor: '#ffffff',
    borderLeftColor: '#ffffff',
    shadowColor: '#a3b1c6',
    shadowOffset: { width: 8, height: 12 },
    shadowOpacity: 0.6,
    shadowRadius: 16,
    elevation: 10
  },
  iconBadge: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#fee2e2',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
    borderTopWidth: 2,
    borderLeftWidth: 2,
    borderTopColor: '#ffffff',
    borderLeftColor: '#ffffff',
    shadowColor: '#cbd5e1',
    shadowOffset: { width: 4, height: 6 },
    shadowOpacity: 0.5,
    shadowRadius: 8,
    elevation: 4
  },
  title: {
    fontSize: 20,
    fontWeight: '800',
    color: '#1e293b',
    marginBottom: 8,
    textAlign: 'center'
  },
  message: {
    fontSize: 14,
    color: '#64748b',
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 20
  },
  buttonRow: {
    flexDirection: 'row',
    gap: 12,
    width: '100%'
  },
  cancelBtn: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 20,
    backgroundColor: '#eef2f6',
    alignItems: 'center',
    borderTopWidth: 2,
    borderLeftWidth: 2,
    borderTopColor: '#ffffff',
    borderLeftColor: '#ffffff',
    shadowColor: '#a3b1c6',
    shadowOffset: { width: 4, height: 6 },
    shadowOpacity: 0.5,
    shadowRadius: 8,
    elevation: 4
  },
  cancelText: {
    fontSize: 15,
    fontWeight: '700',
    color: '#475569'
  },
  logoutBtn: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 20,
    backgroundColor: '#dc2626',
    alignItems: 'center',
    borderTopWidth: 1.5,
    borderLeftWidth: 1.5,
    borderTopColor: '#fca5a5',
    borderLeftColor: '#fca5a5',
    shadowColor: '#dc2626',
    shadowOffset: { width: 4, height: 6 },
    shadowOpacity: 0.4,
    shadowRadius: 8,
    elevation: 6
  },
  logoutText: {
    fontSize: 15,
    fontWeight: '800',
    color: '#ffffff'
  }
});
