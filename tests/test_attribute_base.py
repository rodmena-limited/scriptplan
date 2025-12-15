import unittest

from scriptplan.core.property import (
    AttributeBase,
    AttributeDefinition,
    AttributeOverwrite,
    IntegerAttribute,
    ListAttributeBase,
    StringAttribute,
    deep_clone,
)


class MockProperty:
    """Mock property node for testing."""
    pass


class TestAttributeBase(unittest.TestCase):
    def setUp(self):
        self.property = MockProperty()
        self.defn = AttributeDefinition(
            'test_attr', 'Test Attribute', StringAttribute,
            False, False, False, 'default_value'
        )

    def test_init(self):
        attr = AttributeBase(self.property, self.defn, self.property)
        self.assertEqual(attr.getProperty(), self.property)
        self.assertEqual(attr.getType(), self.defn)
        self.assertEqual(attr.get(), 'default_value')
        self.assertFalse(attr.provided)
        self.assertFalse(attr.inherited)

    def test_reset(self):
        attr = AttributeBase(self.property, self.defn, self.property)
        attr.set('new_value')
        self.assertTrue(attr.provided)
        attr.reset()
        self.assertEqual(attr.get(), 'default_value')
        self.assertFalse(attr.provided)

    def test_set_and_get(self):
        attr = AttributeBase(self.property, self.defn, self.property)
        attr.set('test_value')
        self.assertEqual(attr.get(), 'test_value')
        self.assertTrue(attr.provided)

    def test_inherit(self):
        attr = AttributeBase(self.property, self.defn, self.property)
        attr.inherit('inherited_value')
        self.assertEqual(attr.get(), 'inherited_value')
        self.assertTrue(attr.inherited)
        self.assertFalse(attr.provided)

    def test_mode(self):
        self.assertEqual(AttributeBase.mode(), 0)
        AttributeBase.setMode(1)
        self.assertEqual(AttributeBase.mode(), 1)
        AttributeBase.setMode(0)  # Reset for other tests

    def test_set_with_mode(self):
        attr = AttributeBase(self.property, self.defn, self.property)

        # Mode 0 - provided
        AttributeBase.setMode(0)
        attr.set('value1')
        self.assertTrue(attr.provided)
        self.assertFalse(attr.inherited)

        # Reset
        attr.reset()

        # Mode 1 - inherited
        AttributeBase.setMode(1)
        attr.set('value2')
        self.assertTrue(attr.inherited)

        # Mode 2 - calculated (neither provided nor inherited set)
        attr.reset()
        AttributeBase.setMode(2)
        attr.set('value3')
        self.assertFalse(attr.provided)
        self.assertFalse(attr.inherited)

        # Reset mode
        AttributeBase.setMode(0)

    def test_id_and_name(self):
        attr = AttributeBase(self.property, self.defn, self.property)
        self.assertEqual(attr.id, 'test_attr')
        self.assertEqual(attr.name, 'Test Attribute')

    def test_value_alias(self):
        attr = AttributeBase(self.property, self.defn, self.property)
        attr.set('test')
        self.assertEqual(attr.value, attr.get())

    def test_isNil(self):
        defn = AttributeDefinition('nil_test', 'Nil Test', StringAttribute, False, False, False, None)
        attr = AttributeBase(self.property, defn, self.property)
        self.assertTrue(attr.isNil())
        attr.set('not_nil')
        self.assertFalse(attr.isNil())

    def test_isNil_list(self):
        defn = AttributeDefinition('list_test', 'List Test', ListAttributeBase, False, False, False, [])
        attr = ListAttributeBase(self.property, defn, self.property)
        self.assertTrue(attr.isNil())
        attr.set('item')
        self.assertFalse(attr.isNil())

    def test_isList(self):
        attr = AttributeBase(self.property, self.defn, self.property)
        self.assertFalse(attr.isList())
        self.assertFalse(AttributeBase.isListClass())

    def test_to_s(self):
        attr = AttributeBase(self.property, self.defn, self.property)
        attr.set('string_value')
        self.assertEqual(attr.to_s(), 'string_value')
        self.assertEqual(str(attr), 'string_value')

    def test_to_num(self):
        defn = AttributeDefinition('num_test', 'Num Test', IntegerAttribute, False, False, False, 0)
        attr = AttributeBase(self.property, defn, self.property)
        attr.set(42)
        self.assertEqual(attr.to_num(), 42)

        attr.set('not_a_number')
        self.assertIsNone(attr.to_num())

    def test_to_sort_numeric(self):
        defn = AttributeDefinition('num_test', 'Num Test', IntegerAttribute, False, False, False, 0)
        attr = AttributeBase(self.property, defn, self.property)
        attr.set(42)
        self.assertEqual(attr.to_sort(), 42)

    def test_to_sort_string(self):
        attr = AttributeBase(self.property, self.defn, self.property)
        attr.set('test')
        self.assertEqual(attr.to_sort(), 'test')

    def test_to_sort_list(self):
        defn = AttributeDefinition('list_test', 'List Test', ListAttributeBase, False, False, False, [])
        attr = ListAttributeBase(self.property, defn, self.property)
        attr.set('a')
        attr.set('b')
        self.assertEqual(attr.to_sort(), 'a, b')

    def test_to_tjp(self):
        attr = AttributeBase(self.property, self.defn, self.property)
        attr.set('value')
        self.assertEqual(attr.to_tjp(), 'test_attr value')


class TestListAttributeBase(unittest.TestCase):
    def setUp(self):
        self.property = MockProperty()
        self.defn = AttributeDefinition(
            'list_attr', 'List Attribute', ListAttributeBase,
            False, False, False, []
        )

    def test_init_empty_list(self):
        attr = ListAttributeBase(self.property, self.defn, self.property)
        self.assertEqual(attr.get(), [])

    def test_set_appends(self):
        attr = ListAttributeBase(self.property, self.defn, self.property)
        attr.set('item1')
        attr.set('item2')
        self.assertEqual(attr.get(), ['item1', 'item2'])

    def test_set_extends(self):
        attr = ListAttributeBase(self.property, self.defn, self.property)
        attr.set(['item1', 'item2'])
        self.assertEqual(attr.get(), ['item1', 'item2'])

    def test_isList(self):
        attr = ListAttributeBase(self.property, self.defn, self.property)
        self.assertTrue(attr.isList())
        self.assertTrue(ListAttributeBase.isListClass())

    def test_to_s(self):
        attr = ListAttributeBase(self.property, self.defn, self.property)
        attr.set('a')
        attr.set('b')
        self.assertEqual(attr.to_s(), 'a, b')

    def test_iter(self):
        attr = ListAttributeBase(self.property, self.defn, self.property)
        attr.set(['a', 'b', 'c'])
        items = list(attr)
        self.assertEqual(items, ['a', 'b', 'c'])

    def test_len(self):
        attr = ListAttributeBase(self.property, self.defn, self.property)
        attr.set(['a', 'b', 'c'])
        self.assertEqual(len(attr), 3)


class TestAttributeDefinition(unittest.TestCase):
    def test_init(self):
        defn = AttributeDefinition(
            'test_id', 'Test Name', StringAttribute,
            True, True, True, 'default'
        )
        self.assertEqual(defn.id, 'test_id')
        self.assertEqual(defn.name, 'Test Name')
        self.assertEqual(defn.objClass, StringAttribute)
        self.assertTrue(defn.inheritedFromParent)
        self.assertTrue(defn.inheritedFromProject)
        self.assertTrue(defn.scenarioSpecific)
        self.assertEqual(defn.default, 'default')
        self.assertFalse(defn.userDefined)

    def test_init_with_user_defined(self):
        defn = AttributeDefinition(
            'custom', 'Custom Attr', StringAttribute,
            False, False, False, '', userDefined=True
        )
        self.assertTrue(defn.userDefined)

    def test_isList(self):
        defn1 = AttributeDefinition('s', 'String', StringAttribute, False, False, False, '')
        self.assertFalse(defn1.isList())

        defn2 = AttributeDefinition('l', 'List', ListAttributeBase, False, False, False, [])
        self.assertTrue(defn2.isList())

    def test_repr(self):
        defn = AttributeDefinition('test_id', 'Test Name', StringAttribute, False, False, True, '')
        repr_str = repr(defn)
        self.assertIn('test_id', repr_str)
        self.assertIn('Test Name', repr_str)
        self.assertIn('StringAttribute', repr_str)
        self.assertIn('scenarioSpecific=True', repr_str)

    def test_slots(self):
        defn = AttributeDefinition('test', 'Test', StringAttribute, False, False, False, '')
        with self.assertRaises(AttributeError):
            defn.nonexistent_attr = 'value'


class TestDeepClone(unittest.TestCase):
    def test_deep_clone_list(self):
        original = [1, [2, 3]]
        cloned = deep_clone(original)
        self.assertEqual(original, cloned)
        cloned[1][0] = 99
        self.assertNotEqual(original, cloned)

    def test_deep_clone_dict(self):
        original = {'a': {'b': 1}}
        cloned = deep_clone(original)
        self.assertEqual(original, cloned)
        cloned['a']['b'] = 99
        self.assertNotEqual(original, cloned)


class TestAttributeOverwrite(unittest.TestCase):
    def test_exception(self):
        with self.assertRaises(AttributeOverwrite):
            raise AttributeOverwrite("Test error")


if __name__ == '__main__':
    unittest.main()
