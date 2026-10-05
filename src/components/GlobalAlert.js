import React, { useState, useEffect } from 'react';
import { Alert } from 'react-native';
import ClayAlert from './ClayAlert';

let globalAlertState = null;

export const setupGlobalAlert = () => {
  const originalAlert = Alert.alert;
  
  Alert.alert = (title, message, buttons, options) => {
    if (globalAlertState) {
      let callback = null;
      // If there are buttons, look for an onPress function to fire (like the registration success)
      if (buttons && Array.isArray(buttons)) {
        const btnWithPress = buttons.find(b => typeof b.onPress === 'function');
        if (btnWithPress) {
          callback = btnWithPress.onPress;
        }
      }
      globalAlertState({ visible: true, title: String(title), message: String(message), callback });
    } else {
      // Fallback if component isn't mounted yet
      originalAlert(title, message, buttons, options);
    }
  };
};

export default function GlobalAlertProvider() {
  const [alertState, setAlertState] = useState({ visible: false, title: '', message: '', callback: null });

  useEffect(() => {
    globalAlertState = setAlertState;
    return () => { globalAlertState = null; };
  }, []);

  return (
    <ClayAlert
      visible={alertState.visible}
      title={alertState.title}
      message={alertState.message}
      onClose={() => {
        setAlertState(prev => ({ ...prev, visible: false }));
        if (alertState.callback) {
          alertState.callback();
        }
      }}
    />
  );
}
