#!/usr/bin/env python
'''
Parse a MAVLink protocol XML file and generate a Java implementation

Copyright Zakhar Kvach 2021
Released under GNU GPL version 3 or later
'''
from __future__ import print_function

from builtins import range
from builtins import object

import os
from . import mavparse, mavtemplate

t = mavtemplate.MAVTemplate()


def generate_enums(basename, xml):
    '''generate main header per XML file'''
    directory = os.path.join(basename, '''enums''')
    mavparse.mkdir_p(directory)
    for en in xml.enum:
        f = open(os.path.join(directory, en.name + ".java"), mode='w')
        t.write(f, '''
/* AUTO-GENERATED FILE.  DO NOT MODIFY.
 *
 * This class was automatically generated by the
 * java mavlink generator tool. It should not be modified by hand.
 */

package com.MAVLink.enums;

/** 
 * ${description}
 */
class ${name} {
${{entry:   static final int ${name} = ${value}; /* ${description} |${{param:${description}| }} */
}}
}
            ''', en)
        f.close()


def generate_CRC(directory, xml):
    '''generate CRC definition and crc array per dialect'''
    xml.message_crcs_array = ''
    for msgid, crc in sorted(xml.message_crcs.items()):
        xml.message_crcs_array += '%u: %u,\n    ' % (msgid, crc)
    
    f = open(os.path.join(directory, "crc.dart"), mode='w')
    t.write(f,'''
/* AUTO-GENERATED FILE.  DO NOT MODIFY.
 *
 * This class was automatically generated by the
 * dart mavlink generator tool. It should not be modified by hand.
 */

/// CRC-16/MCRF4XX calculation for MAVlink messages. The checksum must be
/// initialized, updated with which field of the message, and then finished with
/// the message id.
///
class CRC {
  static const Map<int, int> mavlinkMessageCRCs = {
    ${message_crcs_array}
  };

  static const int crcInitValue = 0xffff;

  int _crcValue = 0;

  CRC() {
    startChecksum();
  }

  /// Initialize the buffer for the CRC16/MCRF4XX
  void startChecksum() {
    _crcValue = crcInitValue;
  }

  /// Accumulate the CRC by adding one char at a time.
  ///
  /// The checksum function adds the hash of one char at a time to the 16 bit
  /// checksum (uint16_t).
  ///
  /// @param data new char to hash
  ///
  void updateChecksum(int data) {
    data = data & 0xff; //cast because we want an unsigned type
    int tmp = data ^ (_crcValue & 0xff);
    tmp ^= (tmp << 4) & 0xff;
    _crcValue = ((_crcValue >> 8) & 0xff) ^
        (tmp << 8) ^
        (tmp << 3) ^
        ((tmp >> 4) & 0xf);
  }

  /// Finish the CRC calculation of a message, by running the CRC with the
  /// Magic Byte.
  ///
  /// @param msgid The message id number
  /// @return boolean True if the checksum was successfully finished. Otherwise false
  ///
  bool finishChecksum(int msgid) {
    if (mavlinkMessageCRCs.containsKey(msgid)) {
      updateChecksum(mavlinkMessageCRCs[msgid]!);
      return true;
    }
    return false;
  }

  int getMSB() {
    return ((_crcValue >> 8) & 0xff);
  }

  int getLSB() {
    return (_crcValue & 0xff);
  }
}

        ''',xml)
    
    f.close()


def generate_message_h(directory, m):
    '''generate per-message header for a XML file'''
    f = open(os.path.join(directory, 'msg_%s.dart' % m.name_lower), mode='w')
    m.name_camel_case = camel_case_from_underscores(m.name)
    (path_head, path_tail) = os.path.split(directory)
    if path_tail == "":
        (path_head, path_tail) = os.path.split(path_head)
    t.write(f, '''
/* AUTO-GENERATED FILE.  DO NOT MODIFY.
 *
 * This class was automatically generated by the Dart mavlink generator tool.
 * It should not be modified by hand.
 */

import '../mavlink_message.dart';
import '../mavlink_packet.dart';
import '../mavlink_payload.dart';

/// ${description}
class Msg${name_camel_case} extends MAVLinkMessage {

    static const int MAVLINK_MSG_ID_${name} = ${id};
    static const int MAVLINK_MSG_LENGTH = ${wire_length};

    ${{ordered_fields:  
    /// ${description}
    late ${array_prefix}${type} ${name}${array_suffix};
    }}

    /// Generates the payload for a mavlink message for a message of this type
    @override
    MAVLinkPacket pack() {
        MAVLinkPacket packet = MAVLinkPacket.ofSpecificLengthAndVersion(MAVLINK_MSG_LENGTH, isMavlink2);
        packet.sysid = 255;
        packet.compid = 190;
        packet.msgid = MAVLINK_MSG_ID_${name};

        ${{base_fields:${packField}
        }}
        if (isMavlink2) {
            ${{extended_fields: ${packField}
            }}
        }
        return packet;
    }

    /// Decode a ${name_lower} message into this class fields
    /// @param payload The message to decode
    @override
    void unpack(MAVLinkPayload payload) {
        payload.resetIndex();

        ${{base_fields:${unpackField}
        }}
        if (isMavlink2) {
            ${{extended_fields: ${unpackField}
            }}
        }
    }

    /// Constructor for a new message, 
    /// initializes the message with the payload from a mavlink packet
    Msg${name_camel_case}.fromPacket(MAVLinkPacket mavLinkPacket) {
        msgid = MAVLINK_MSG_ID_${name};

        sysid = mavLinkPacket.sysid;
        compid = mavLinkPacket.compid;
        isMavlink2 = mavLinkPacket.isMavlink2;
        unpack(mavLinkPacket.payload);
    }

    ${{ordered_fields: ${getText} }}
    
    /// Returns a string with the MSG name and data
    @override
    String toString() {
        return 'MAVLINK_MSG_ID_${name} - sysid: $sysid, compid: $compid ${{ordered_fields: ${name}: $${name}}}';
    }

    /// Returns a human-readable string of the name of the message
    @override
    String name() {
        return "MAVLINK_MSG_ID_${name}";
    }
}
        ''', m)
    f.close()


def generate_MAVLinkMessage(directory, xml_list):
    f = open(os.path.join(directory, "MAVLinkPacket.java"), mode='w')

    imports = []

    for xml in xml_list:
        importString = "import com.MAVLink.{}.*;".format(xml.basename)
        imports.append(importString)

    xml_list[0].importString = os.linesep.join(imports)

    t.write(f, '''
/* AUTO-GENERATED FILE.  DO NOT MODIFY.
 *
 * This class was automatically generated by the
 * java mavlink generator tool. It should not be modified by hand.
 */

package com.MAVLink;

import java.io.Serializable;
import com.MAVLink.Messages.MAVLinkPayload;
import com.MAVLink.Messages.MAVLinkMessage;
import com.MAVLink.${basename}.CRC;

${importString}

/**
 * Common interface for all MAVLink Messages
 * Packet Anatomy
 * This is the anatomy of one packet. It is inspired by the CAN and SAE AS-4 standards.
 *
 * MAVLink 1 Packet Format
 *
 * Byte Index  Content              Value       Explanation
 * 0            Packet start sign  v1.0: 0xFE   Indicates the start of a new packet.  (v0.9: 0x55; v1.0: 0xFE; v2.0 0xFD)
 * 1            Payload length      0 - 255     Indicates length of the following payload.
 * 2            Packet sequence     0 - 255     Each component counts up its send sequence. Allows to detect packet loss
 * 3            System ID           1 - 255     ID of the SENDING system. Allows to differentiate different MAVs on the same network.
 * 4            Component ID        0 - 255     ID of the SENDING component. Allows to differentiate different components of the same system, e.g. the IMU and the autopilot.
 * 5            Message ID          0 - 255     ID of the message - the id defines what the payload means and how it should be correctly decoded.
 * 6 to (n+6)   Payload             0 - 255     Data of the message, depends on the message id.
 * (n+7)to(n+8) Checksum (low byte, high byte)  CRC16/MCRF4XX hash, excluding packet start sign, so bytes 1..(n+6) Note: The checksum also includes MAVLINK_CRC_EXTRA (Number computed from message fields. Protects the packet from decoding a different version of the same packet but with different variables).
 *
 * The checksum is the CRC16/MCRF4XX. Please see the MAVLink source code for a documented C-implementation of it. LINK TO CHECKSUM
 * The minimum packet length is 8 bytes for acknowledgement packets without payload
 * The maximum packet length is 263 bytes for full payload
 *
 *
 * MAVLink 2 Packet Format
 *
 * Byte Index     Content             Value              Explanation
 * 0              Packet start sign  v2.0: 0xFD          Indicates the start of a new packet.  (v0.9: 0x55; v1.0: 0xFE; v2.0 0xFD)
 * 1              Payload length      0 - 255            Indicates length of the following payload.
 * 2              Incompatible Flags  0 - 255            Flags that must be understood
 * 3              Compatible Flags    0 - 255            Flags that can be ignored if not understood
 * 4              Packet sequence     0 - 255            Each component counts up its send sequence. Allows to detect packet loss
 * 5              System ID           1 - 255            ID of the SENDING system. Allows to differentiate different MAVs on the same network.
 * 6              Component ID        0 - 255            ID of the SENDING component. Allows to differentiate different components of the same system, e.g. the IMU and the autopilot.
 * 7 to 9         Message ID          0 - 16777216       ID of the message - the id defines what the payload means and how it should be correctly decoded.
 * 10             Target System ID    1 - 255            (OPTIONAL) ID of the TARGET system. Only used for point-to-point mode
 * 11             Target Component ID 0 - 255            (OPTIONAL) ID of the TARGET component. Only used for point-to-point mode
 * 12 to (n+12)   Payload             0 - 255            Data of the message, depends on the message id.
 * (n+13)to(n+14) Checksum (low byte, high byte)         CRC16/MCRF4XX hash, excluding packet start sign, so bytes 1..(n+6) Note: The checksum also includes MAVLINK_CRC_EXTRA (Number computed from message fields. Protects the packet from decoding a different version of the same packet but with different variables).
 * (n+15)to(n+27) Signature (typeid, timestamp, sha256)  (OPTIONAL) Signature which allows ensuring that the link is tamper-proof; 13 bytes containing typeid (1 byte), timestamp (6 bytes), and last 6 bytes of SHA256 hash
 *
 * The signature is a combination of a typeid, timestamp, and SHA256 hash.
 * OPTIONAL fields mean that, if they are not used, they do not exist in the MAVLink frame at all. Typically target sysid and target compid are not used, and signature is only used if signing is set up between both ends.
 * 
 * @see <a href="https://mavlink.io">mavlink.io</a> for more documentation on the MAVLink protocol
 */
class MAVLinkPacket implements Serializable {
    private static final long serialVersionUID = 2095947771227815314L;

    static final int MAVLINK_STX_MAVLINK1 = 0xFE; // 254
    static final int MAVLINK_STX_MAVLINK2 = 0xFD; // 253
    static final int MAVLINK1_HEADER_LEN = 6;
    static final int MAVLINK2_HEADER_LEN = 10;
    static final int MAVLINK1_NONPAYLOAD_LEN = MAVLINK1_HEADER_LEN + 2;
    static final int MAVLINK2_NONPAYLOAD_LEN = MAVLINK2_HEADER_LEN + 2;

    static final boolean V = false;
    static void logv(String str) {
        if(V) System.out.println(String.format("MAVLinkPacket: %s", str));
    }

    /**
     * Payload length
     */
    final int len;

    /**
     * Message sequence
     */
    int seq;

    /**
     * ID of the SENDING system. Allows to differentiate different MAVs on the
     * same network.
     */
    int sysid;

    /**
     * ID of the SENDING component. Allows to differentiate different components
     * of the same system, e.g. the IMU and the autopilot.
     */
    int compid;

    /**
     * ID of the message - the id defines what the payload means and how it
     * should be correctly decoded.
     */
    int msgid;

    /**
     * Data of the message, depends on the message id.
     */
    MAVLinkPayload payload;

    /**
    * CRC-16/MCRF4XX hash, excluding packet start sign, so bytes 1..(n+HEADER-LENGTH)
    * Note: The checksum also includes MAVLINK_CRC_EXTRA (Number computed from
    * message fields. Protects the packet from decoding a different version of
    * the same packet but with different variables).
    */
    CRC crc;

    // MAVLink 2.0 fields

    /**
     * Flag to indicate which MAVLink version this packet is
     */
    boolean isMavlink2;

    /**
     * Flags that must be understood
     */
    int incompatFlags;

    /**
     * Flags that can be ignored if not understood
     */
    int compatFlags;

    MAVLinkPacket(int payloadLength) {
        this(payloadLength, false);
    }

    MAVLinkPacket(final int payloadLength, final boolean isMavlink2) {
        len = payloadLength;
        payload = new MAVLinkPayload();
        isMavlink2 = isMavlink2;
    }

    /**
     * Check if the size of the Payload is equal to the "len" byte
     */
    boolean payloadIsFilled() {
        return payload.size() >= len;
    }

    /**
     * Update CRC for this packet.
     * @return boolean True if the CRC was successfully updated. Otherwise false
     */
    boolean generateCRC(final int payloadSize) {
        if (crc == null) {
            crc = new CRC();
        } else {
            crc.start_checksum();
        }

        if (isMavlink2) {
            crc.update_checksum(payloadSize);
            crc.update_checksum(incompatFlags);
            crc.update_checksum(compatFlags);
            crc.update_checksum(seq);
            crc.update_checksum(sysid);
            crc.update_checksum(compid);
            crc.update_checksum(msgid);
            crc.update_checksum(msgid >>> 8);
            crc.update_checksum(msgid >>> 16);
        } else {
            crc.update_checksum(payloadSize);
            crc.update_checksum(seq);
            crc.update_checksum(sysid);
            crc.update_checksum(compid);
            crc.update_checksum(msgid);
        }

        payload.resetIndex();

        for (int i = 0; i < payloadSize; i++) {
            crc.update_checksum(payload.getByte());
        }
        return crc.finish_checksum(msgid);
    }

    /**
     * Return length of actual data after triming zeros at the end.
     * @param payload
     * @return minimum length of valid data
     */
    private int mavTrimPayload(final byte[] payload)
    {
        int length = payload.length;
        while (length > 1 && payload[length-1] == 0) {
            length--;
        }
        return length;
    }

    /**
     * Encode this packet for transmission.
     *
     * @return Array with bytes to be transmitted
     */
    byte[] encodePacket() {
        final int bufLen;
        final int payloadSize;

        if (isMavlink2) {
            payloadSize = mavTrimPayload(payload.payload.array());
            bufLen = MAVLINK2_HEADER_LEN + payloadSize + 2;
        } else {
            payloadSize = payload.size();
            bufLen = MAVLINK1_HEADER_LEN + payloadSize + 2;

        }
        byte[] buffer = new byte[bufLen];

        int i = 0;
        if (isMavlink2) {
            buffer[i++] = (byte) MAVLINK_STX_MAVLINK2;
            buffer[i++] = (byte) payloadSize;
            buffer[i++] = (byte) incompatFlags;
            buffer[i++] = (byte) compatFlags;
            buffer[i++] = (byte) seq;
            buffer[i++] = (byte) sysid;
            buffer[i++] = (byte) compid;
            buffer[i++] = (byte) (msgid & 0XFF);
            buffer[i++] = (byte) ((msgid >>> 8) & 0XFF);
            buffer[i++] = (byte) ((msgid >>> 16) & 0XFF);
        } else {
            buffer[i++] = (byte) MAVLINK_STX_MAVLINK1;
            buffer[i++] = (byte) payloadSize;
            buffer[i++] = (byte) seq;
            buffer[i++] = (byte) sysid;
            buffer[i++] = (byte) compid;
            buffer[i++] = (byte) msgid;
        }

        for (int j = 0; j < payloadSize; ++j) {
            buffer[i++] = payload.payload.get(j);
        }

        generateCRC(payloadSize);
        buffer[i++] = (byte) (crc.getLSB());
        buffer[i++] = (byte) (crc.getMSB());

        logv(String.format("encode: isMavlink2=%s msgid=%d", isMavlink2, msgid));

        return buffer;
    }
        ''', xml_list[0])

    f.write('''
    /**
     * Unpack the data in this packet and return a MAVLink message
     *
     * @return MAVLink message decoded from this packet
     */
    MAVLinkMessage unpack() {
        switch (msgid) {
        ''')

    # sort msgs by id
    xml_msgs = []
    for xml in xml_list:
        for msg in xml.message:
            xml_msgs.append(msg)
    xml_msgs.sort(key=lambda msg: msg.id)

    for msg in xml_msgs:
        t.write(f, ''' 
            case msg_${name_lower}.MAVLINK_MSG_ID_${name}:
                return  new msg_${name_lower}(this);
            ''', msg)
    f.write('''
            default:
                return null;
        }
    }
''')

    f.write('''
}
''')
    f.close()


def copy_fixed_headers(directory, xml):
    '''copy the fixed protocol headers to the target directory'''
    import shutil
    hlist = ['Parser.java', 'Messages/MAVLinkMessage.java', 'Messages/MAVLinkPayload.java',
             'Messages/MAVLinkStats.java']
    basepath = os.path.dirname(os.path.realpath(__file__))
    srcpath = os.path.join(basepath, 'java/lib')
    print("Copying fixed headers")
    for h in hlist:
        src = os.path.realpath(os.path.join(srcpath, h))
        dest = os.path.realpath(os.path.join(directory, h))
        if src == dest:
            continue
        destdir = os.path.realpath(os.path.join(directory, 'Messages'))
        try:
            os.makedirs(destdir)
        except:
            print("Not re-creating Messages directory")
        shutil.copy(src, dest)


class mav_include(object):
    def __init__(self, base):
        self.base = base


def mavfmt(field, typeInfo=0):
    '''work out the struct format for a type'''
    map = {
        'float': ('double', 'Float'),
        'double': ('double', 'Double'),
        'char': ('int', 'Int8'),
        'int8_t': ('int', 'Int8'),
        'uint8_t': ('int', 'Uint8'),
        'uint8_t_mavlink_version': ('int', 'Uint8'),
        'int16_t': ('int', 'Int16'),
        'uint16_t': ('int', 'Uint16'),
        'int32_t': ('int', 'Int32'),
        'uint32_t': ('int', 'Uint32'),
        'int64_t': ('int', 'Int64'),
        'uint64_t': ('int', 'Uint64'), #TODO correct type
    }

    return map[field.type][typeInfo]


def generate_one(basename, xml):
    '''generate headers for one XML file'''

    directory = os.path.join(basename, xml.basename)

    print("Generating Dart implementation in directory %s" % directory)
    mavparse.mkdir_p(directory)

    if xml.little_endian:
        xml.mavlink_endian = "MAVLINK_LITTLE_ENDIAN"
    else:
        xml.mavlink_endian = "MAVLINK_BIG_ENDIAN"

    if xml.crc_extra:
        xml.crc_extra_define = "1"
    else:
        xml.crc_extra_define = "0"

    if xml.sort_fields:
        xml.aligned_fields_define = "1"
    else:
        xml.aligned_fields_define = "0"

    # work out the included headers
    xml.include_list = []
    for i in xml.include:
        base = i[:-4]
        xml.include_list.append(mav_include(base))

    # form message lengths array
    xml.message_lengths_array = ''
    for mlen in xml.message_lengths:
        xml.message_lengths_array += '%u, ' % mlen
    xml.message_lengths_array = xml.message_lengths_array[:-2]

    # form message info array
    xml.message_info_array = ''
    for name in xml.message_names:
        if name is not None:
            xml.message_info_array += 'MAVLINK_MESSAGE_INFO_%s, ' % name
        else:
            # Several C compilers don't accept {NULL} for
            # multi-dimensional arrays and structs
            # feed the compiler a "filled" empty message
            xml.message_info_array += '{"EMPTY",0,{{"","",MAVLINK_TYPE_CHAR,0,0,0}}}, '
    xml.message_info_array = xml.message_info_array[:-2]

    # add some extra field attributes for convenience with arrays
    for m in xml.message:
        m.msg_name = m.name
        if xml.crc_extra:
            m.crc_extra_arg = ", %s" % m.crc_extra
        else:
            m.crc_extra_arg = ""
        for f in m.fields:
            if f.print_format is None:
                f.c_print_format = 'NULL'
            else:
                f.c_print_format = '"%s"' % f.print_format
            f.getText = ''
            if f.array_length != 0:
                f.array_suffix = ' = List<%s>.filled(%u, 0)' % (mavfmt(f), f.array_length)
                f.array_suffix_empty = '[]'
                f.array_prefix = 'List<'
                f.array_tag = '_array'
                f.array_arg = ', %u' % f.array_length
                f.array_return_arg = '%s, %u, ' % (f.name, f.array_length)
                f.array_const = 'const '
                f.decode_left = ''
                f.decode_right = 'm.%s' % (f.name)

                # TODO iterate in Dart's style
                f.unpackField = ''' 
        for (int i = 0; i < %s.length; i++) { 
            %s[i] = payload.get%s();
        }
                ''' % (f.name, f.name, mavfmt(f, 1))
                f.packField = '''
        for (int i = 0; i < %s.length; i++) {
            packet.payload.put%s(%s[i]);
        }
                    ''' % (f.name, mavfmt(f, 1), f.name)
                f.return_type = 'uint16_t'
                f.get_arg = ', %s *%s' % (f.type, f.name)
                if f.type == 'char':

                    f.c_test_value = '"%s"' % f.test_value
                    f.getText = '''
    /**
    * Sets the buffer of this message with a string, adds the necessary padding
    */
    void set%s(String str) {
        int len = Math.min(str.length(), %d);
        for (int i=0; i<len; i++) {
            %s[i] = (byte) str.charAt(i);
        }

        for (int i=len; i<%d; i++) {            // padding for the rest of the buffer
            %s[i] = 0;
        }
    }

    /**
    * Gets the message, formated as a string
    */
    String get%s() {
        StringBuffer buf = new StringBuffer();
        for (int i = 0; i < %d; i++) {
            if (%s[i] != 0)
                buf.append((char) %s[i]);
            else
                break;
        }
        return buf.toString();

    }
                        ''' % (
                        f.name.title(), f.array_length, f.name, f.array_length, f.name, f.name.title(), f.array_length,
                        f.name, f.name)
                else:
                    test_strings = []
                    for v in f.test_value:
                        test_strings.append(str(v))
                    f.c_test_value = '{ %s }' % ', '.join(test_strings)
            else:
                f.array_suffix = ''
                f.array_suffix_empty = ''
                f.array_prefix = ''
                f.array_tag = ''
                f.array_arg = ''
                f.array_return_arg = ''
                f.array_const = ''
                f.decode_left = '%s' % (f.name)
                f.decode_right = ''
                f.unpackField = '%s = payload.get%s();' % (f.name, mavfmt(f, 1))
                f.packField = 'packet.payload.put%s(%s);' % (mavfmt(f, 1), f.name)

                f.get_arg = ''
                f.return_type = f.type
                if f.type == 'char':
                    f.c_test_value = "'%s'" % f.test_value
                elif f.type == 'uint64_t':
                    f.c_test_value = "%sULL" % f.test_value
                elif f.type == 'int64_t':
                    f.c_test_value = "%sLL" % f.test_value
                else:
                    f.c_test_value = f.test_value

    # cope with uint8_t_mavlink_version
    for m in xml.message:
        m.arg_fields = []
        m.array_fields = []
        m.scalar_fields = []
        for f in m.ordered_fields:
            if f.array_length != 0:
                m.array_fields.append(f)
            else:
                m.scalar_fields.append(f)
        for f in m.fields:
            if not f.omit_arg:
                m.arg_fields.append(f)
                f.putname = f.name
            else:
                f.putname = f.const_value

    # fix types to java
    for m in xml.message:
        for f in m.ordered_fields:
            f.type = mavfmt(f)

    # separate base fields from MAVLink 2 extended fields
    for m in xml.message:
        m.base_fields = m.ordered_fields[:m.extensions_start]
        m.extended_fields = []
        if m.extensions_start is not None:
            m.extended_fields = m.ordered_fields[m.extensions_start:]

    generate_CRC(directory, xml)

    for m in xml.message:
        generate_message_h(directory, m)


def generate(basename, xml_list):
    '''generate complete MAVLink Java implemenation'''
    for xml in xml_list:
        generate_one(basename, xml)
        generate_enums(basename, xml)
        generate_MAVLinkMessage(basename, xml_list)
    copy_fixed_headers(basename, xml_list[0])

def camel_case_from_underscores(string):
    """generate a CamelCase string from an underscore_string."""
    components = string.lower().split('_')
    string = ''
    for component in components:
        string += component[0].upper() + component[1:]
    return string

def lower_camel_case_from_underscores(string):
    """generate a lower-cased camelCase string from an underscore_string.
    For example: my_variable_name -> myVariableName"""
    components = string.lower().split('_')
    string = components[0]
    for component in components[1:]:
        string += component[0].upper() + component[1:]
    return string
