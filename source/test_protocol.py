import unittest
import protocol
import struct

class TestMessageProtocol(unittest.TestCase):
    def _create_protocol(self):
        return protocol.create_text_message_protocol(0)

    def test_protocol_returns_correct_type_code(self):
        protocol = self._create_protocol()
        self.assertEqual(protocol.get_type_code(), 0)

    def test_protocol_is_not_fixed_length(self):
        protocol = self._create_protocol()
        self.assertFalse(protocol.is_fixed_length())

    def test_correctly_unpacks_field_length(self):
        field_length = struct.pack(">H", 20)
        protocol = self._create_protocol()
        unpacked_field_length = protocol.unpack_field_length(0, field_length, 0)
        self.assertEqual(unpacked_field_length, 20)

    def test_correctly_unpacks_text(self):
        text = "This is a test"
        encoded_text = text.encode("utf-8")
        packed_text = struct.pack(">" + str(len(encoded_text)) + "s", encoded_text)
        protocol = self._create_protocol()
        unpacked_text = protocol.unpack_variable_length_field(0, len(encoded_text), packed_text, 0)
        self.assertEqual(unpacked_text, text)
    
    def test_gives_correct_field_information(self):
        protocol = self._create_protocol()
        expected_field_name = "text"
        expected_max_size = 2
        self.assertTrue(protocol.is_last_field(0))
        self.assertEqual(protocol.compute_variable_length_field_max_size(0), expected_max_size)
        self.assertEqual(protocol.compute_field_name(0), expected_field_name)

    def test_correctly_packs_text(self):
        protocol = self._create_protocol()
        text = "testing"
        encoded_text = text.encode("utf-8")
        text_length = len(encoded_text)
        expected = struct.pack(">BH" + str(text_length) + "s", 0, text_length, encoded_text)
        packed_text = protocol.pack(text)
        self.assertEqual(expected, packed_text)

class TestSingleFieldFixedLengthProtocol(unittest.TestCase):
    def _create_protocol(self):
        return protocol.create_single_byte_nonnegative_integer_message_protocol(12)
    
    def test_computes_correct_field_string(self):
        expected = ">B"
        actual = self._create_protocol().compute_fields_string()
        self.assertEqual(expected, actual)
    
    def test_can_correctly_pack_argument(self):
        value = 10
        protocol = self._create_protocol()
        actual = protocol.pack(value)
        expected = struct.pack(">BB", 12, 10)
        self.assertEqual(actual, expected)

    def test_returns_correct_type_code(self):
        expected = 12
        actual = self._create_protocol().get_type_code()
        self.assertEqual(expected, actual)

    def test_can_correctly_unpack_message(self):
        protocol = self._create_protocol()
        input_bytes = struct.pack(">B", 100)
        expected_result = {'number': 100}
        actual_result = protocol.unpack(input_bytes)
        self.assertEqual(expected_result, actual_result)

    def test_returns_correct_size(self):
        protocol = self._create_protocol()
        expected = 1
        actual = protocol.get_size()
        self.assertEqual(actual, expected)

    def test_returns_correct_number_of_fields(self):
        protocol = self._create_protocol()
        expected = 1
        actual = protocol.get_number_of_fields()
        self.assertEqual(actual, expected)

def encode_text(text):
    return text.encode("utf-8")

def decode_text(input_bytes):
    return input_bytes.decode("utf-8")

def create_complex_variable_length_message_protocol(type_code = 2):
    first_field = protocol.create_string_protocol_field('name', 2)
    second_field = protocol.create_string_protocol_field('password', 1)
    third_field = protocol.create_single_byte_nonnegative_integer_protocol_field('type')
    result = protocol.VariableLengthMessageProtocol(type_code, [first_field, second_field, third_field])
    return result

class TestComplexVariableLengthMessageProtocol(unittest.TestCase):
    def _create_protocol(self):
        return create_complex_variable_length_message_protocol()

    def _create_packed_example(self):
        name = 'bob versus chuck'
        password = '1'*100    
        game_type = 30
        encoded_name = encode_text(name)
        encoded_password = encode_text(password)
        packing = struct.pack(">BH16sB100sB", 2, 16, encoded_name, 100, encoded_password, game_type)
        values = {'name': name, 'password': password, 'type': game_type}
        return packing, values

    def test_can_correctly_pack_values(self):
        protocol = self._create_protocol()
        expected, values = self._create_packed_example()
        actual = protocol.pack(values['name'], values['password'], values['type'])
        self.assertEqual(expected, actual)

    def test_can_correctly_unpack_values(self):
        message_protocol = self._create_protocol()
        protocol_map = protocol.ProtocolMap([message_protocol])
        message_handler = protocol.MessageHandler(protocol_map)
        packing, expected = self._create_packed_example()
        message_handler.receive_bytes(packing)
        values = message_handler.get_values()
        self.assertEqual(len(expected), len(values))
        for key in expected:
            self.assertEqual(expected[key], values[key])
        self.assertTrue(message_handler.is_done_obtaining_values())

class TestMultipleFieldFixedLengthMessageProtocol(unittest.TestCase):
    def _compute_protocol(self):
        first_field = protocol.create_single_byte_nonnegative_integer_protocol_field('1')
        second_field = protocol.create_single_byte_nonnegative_integer_protocol_field('2')
        result = protocol.FixedLengthMessageProtocol(100, [first_field, second_field])
        return result

    def test_has_correct_size(self):
        expected = 2
        actual = self._compute_protocol().get_size()
        self.assertEqual(expected, actual)

    def test_has_correct_number_of_fields(self):
        expected = 2
        actual = self._compute_protocol().get_number_of_fields()
        self.assertEqual(expected, actual)

    def _create_pack_and_values(self):
        first_value = 90
        second_value = 0
        values = {"1": first_value, "2": second_value}
        packing = struct.pack(">BBB", 100, first_value, second_value)
        return packing, values

    def test_can_pack_values_correctly(self):
        message_protocol = self._compute_protocol()
        expected, values = self._create_pack_and_values()
        actual = message_protocol.pack(values["1"], values["2"])
        self.assertEqual(expected, actual)

    def test_can_unpack_values_correctly(self):
        message_protocol = self._compute_protocol()
        pack, expected = self._create_pack_and_values()
        pack = pack[1:]
        actual = message_protocol.unpack(pack)
        self.assertEqual(expected, actual)

def create_values_dictionary(values, names):
    result = {}
    for i in range(len(values)):
        result[names[i]] = values[i]
    return result

class TestMessageHandler(unittest.TestCase):
    def _create_protocol_map(self):
        message_protocol = protocol.create_text_message_protocol(0)
        nonnegative_integer_protocol = protocol.create_single_byte_nonnegative_integer_message_protocol(1)
        protocol_map = protocol.ProtocolMap([message_protocol, nonnegative_integer_protocol])
        return protocol_map
    
    def _create_values_and_names(self):
        return [['message'], [1]], [['text'], ['number']]
    
    def _create_more_complex_protocol_map(self):
        variable_length_protocol = create_complex_variable_length_message_protocol(0)
        bigger_fixed_length_field = protocol.ConstantLengthProtocolField('big', "2s", 2)
        small_field = protocol.create_single_byte_nonnegative_integer_protocol_field('small')
        fixed_length_protocol = protocol.FixedLengthMessageProtocol(1, [bigger_fixed_length_field, small_field])
        fieldless_protocol = protocol.create_protocol(2)
        protocol_map = protocol.ProtocolMap([variable_length_protocol, fixed_length_protocol, fieldless_protocol])
        return protocol_map

    def _create_more_complex_values_and_names(self):
        return [["a"*1000, "b"*5, 9], ["sm", 126], []], [['name', 'password', 'type'], ['big', 'small'], []]

    def test_handles_full_values(self):
        protocol_map = self._create_protocol_map()
        values, names = self._create_values_and_names()
        message_handler = protocol.MessageHandler(protocol_map)
        for i in range(len(values)):
            packing = protocol_map.pack_values_given_type_code(i, *values[i])
            message_handler.receive_bytes(packing)
            self.assertTrue(message_handler.is_done_obtaining_values())
            expected = create_values_dictionary(values[i], names[i])
            actual = message_handler.get_values()
            self.assertEqual(expected, actual)
            expected_type_code = i
            actual_type_code = message_handler.get_protocol().get_type_code()
            self.assertEqual(expected_type_code, actual_type_code)
            message_handler.prepare_for_next_message()

    def _assert_handles_single_byte_at_a_time_given_map_values_and_names(self, protocol_map, values, names):
        message_handler = protocol.MessageHandler(protocol_map)
        for i in range(len(values)):
            packing = protocol_map.pack_values_given_type_code(i, *values[i])
            for j in range(len(packing)):
                byte = packing[j:j+1]
                self.assertFalse(message_handler.is_done_obtaining_values())
                message_handler.receive_bytes(byte)
            self.assertTrue(message_handler.is_done_obtaining_values())
            expected = create_values_dictionary(values[i], names[i])
            actual = message_handler.get_values()
            self.assertEqual(expected, actual)
            expected_type_code = i
            actual_type_code = message_handler.get_protocol().get_type_code()
            self.assertEqual(expected_type_code, actual_type_code)
            message_handler.prepare_for_next_message()

    def test_handles_single_byte_at_a_time(self):
        protocol_map = self._create_protocol_map()
        values, names = self._create_values_and_names()
        self._assert_handles_single_byte_at_a_time_given_map_values_and_names(protocol_map, values, names)

    def test_handle_single_byte_at_a_time_with_more_complex_protocols(self):
        protocol_map = self._create_more_complex_protocol_map()
        values, names = self._create_more_complex_values_and_names()
        self._assert_handles_single_byte_at_a_time_given_map_values_and_names(protocol_map, values, names)

class TestTypeCodeOnlyMessageProtocol(unittest.TestCase):
    def _create_protocol(self):
        return protocol.create_fieldless_message_protocol(9)

    def test_returns_correct_type_code(self):
        expected = 9
        actual = self._create_protocol().get_type_code()
        self.assertEqual(expected, actual)

    def test_has_no_fields(self):
        expected = 0
        actual = self._create_protocol().get_number_of_fields()
        self.assertEqual(expected, actual)

    def test_packs_correctly(self):
        expected = struct.pack(">B", 9)
        actual = self._create_protocol().pack()
        self.assertEqual(expected, actual)

    def test_protocol_map_packs_correctly(self):
        simple_map = protocol.ProtocolMap([self._create_protocol()])
        expected = struct.pack(">B", 9)
        actual = simple_map.pack_values_given_type_code(9, {})
        self.assertEqual(expected, actual)

if __name__ == '__main__':
    unittest.main()