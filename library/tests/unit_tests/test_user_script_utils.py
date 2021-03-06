import ast
import asyncio
import pathlib
import unittest

from greppo.input_types import GreppoInputsNames
from meta.asttools import cmp_ast
from meta.asttools import print_ast
from greppo.user_script_utils import append_send_data_method, ReplaceGpoVariableWithValueTransformer
from greppo.user_script_utils import RenameGreppoAppTransformer
from greppo.user_script_utils import script_task


def hex_token_generator(nbytes):
    if nbytes == 4:
        return "somehex1"
    return 0


class TestUserScriptUtils(unittest.TestCase):
    def test_transformer_for_number_input(self):
        transformer = ReplaceGpoVariableWithValueTransformer(
            input_updates={}, hex_token_generator=hex_token_generator,
        )
        user_code = ast.parse(
            'number_1 = gpo.number(value=10, name="Number input 1")', "<test>"
        )

        transformer.visit(user_code)

        expected_user_code = ast.parse(
            "number_1 = 10",
            "<test>",
        )

        self.assertTrue(cmp_ast(user_code, expected_user_code))

    def test_transformer_for_number_input_with_input_update(self):
        transformer = ReplaceGpoVariableWithValueTransformer(
            input_updates={"Number input 1": 11}, hex_token_generator=hex_token_generator,
        )
        user_code = ast.parse(
            'number_1 = gpo.number(value=10, name="Number input 1")', "<test>"
        )

        transformer.visit(user_code)

        expected_user_code = ast.parse(
            "number_1 = 11",
            "<test>",
        )

        self.assertTrue(cmp_ast(user_code, expected_user_code))

    def test_transformer_for_multiselect_no_input_update(self):
        transformer = ReplaceGpoVariableWithValueTransformer(
            input_updates={}, hex_token_generator=hex_token_generator,
        )
        user_code = ast.parse(
            'multiselect1=gpo.multiselect(name="Second selector", options=[1, "True", "France"], default=["a"])'
        )

        transformer.visit(user_code)

        expected_user_code = ast.parse(
            'multiselect1 = ["a"]',
            "<test>",
        )

        self.assertTrue(cmp_ast(user_code, expected_user_code))

    def test_transformer_for_multiselect_with_input_update(self):
        transformer = ReplaceGpoVariableWithValueTransformer(
            input_updates={"Second selector": ["b"]}, hex_token_generator=hex_token_generator,
        )
        user_code = ast.parse(
            'multiselect1=gpo.multiselect(name="Second selector", options=[1, "True", "France"], default=["a"])'
        )

        transformer.visit(user_code)

        expected_user_code = ast.parse(
            'multiselect1 = ["b"]',
            "<test>",
        )

        self.assertTrue(cmp_ast(user_code, expected_user_code))

    def test_transformer_for_multiselect_with_input_update_empty_value(self):
        # TODO this should be fixed, we cannot have an empty value for multiselect input.
        transformer = ReplaceGpoVariableWithValueTransformer(
            input_updates={"Second selector": ""}, hex_token_generator=hex_token_generator,
        )
        user_code = ast.parse(
            'multiselect1=gpo.multiselect(name="Second selector", options=[1, "True", "France"], default=["a"])'
        )

        transformer.visit(user_code)

        expected_user_code = ast.parse(
            'multiselect1 = ""',
            "<test>",
        )

        self.assertTrue(cmp_ast(user_code, expected_user_code))

    def test_transformer_for_all_inputs_no_arg_check(self):
        transformer = ReplaceGpoVariableWithValueTransformer(
            input_updates={}, hex_token_generator=hex_token_generator,
        )

        input_names = GreppoInputsNames
        for input_name in input_names:
            with self.subTest():
                user_code = ast.parse("select1 = gpo.{}()".format(input_name), "<test>")

                transformer.visit(user_code)

                expected_user_code = ast.parse(
                    "select1 = null",
                    "<test>",
                )

                print_ast(user_code)
                print_ast(expected_user_code)

                self.assertTrue(cmp_ast(user_code, expected_user_code))

    def test_transformer_for_gpo_name(self):
        hash_prefix = hex_token_generator(nbytes=4)
        transformer = RenameGreppoAppTransformer(hash_prefix=hash_prefix)

        user_code = ast.parse(
            "select1 = app.select(name='somehex1_First selector', "
            "options=['a', 'b', 'c'], default='a', input_updates={})",
            "<test>",
        )

        transformer.visit(user_code)

        expected_user_code = ast.parse(
            "select1 = somehex1_app.select(name='somehex1_First selector', "
            "options=['a', 'b', 'c'], default='a', input_updates={})",
            "<test>",
        )

        self.assertTrue(cmp_ast(user_code, expected_user_code))

    def test_append_send_data_method(self):
        user_code = append_send_data_method(ast.parse(''))
        ast.fix_missing_locations(user_code)

        expected_code = ast.parse('gpo_payload = app.gpo_prepare_data()')

        self.assertTrue(cmp_ast(user_code, expected_code))


class TestRunUserScript(unittest.TestCase):
    def test_user_script_exception(self):
        dir_path = pathlib.Path(__file__).parent.resolve()
        user_script_path = dir_path.joinpath("user_script_1.py")

        with self.assertRaises(SyntaxError) as context:
            asyncio.run(
                script_task(script_name=str(user_script_path), input_updates={})
            )

        self.assertEqual("unexpected EOF while parsing", context.exception.msg)
        self.assertEqual(3, context.exception.lineno)

    def test_user_script_works(self):
        dir_path = pathlib.Path(__file__).parent.resolve()
        user_script_path = dir_path.joinpath("user_script_4.py")

        payload = asyncio.run(
            script_task(
                script_name=str(user_script_path),
                input_updates={},
                hex_token_generator=hex_token_generator,
            )
        )

        expected_payload = {
            "base_layer_info": [],
            "overlay_layer_data": [],
            "component_info": [
                {
                    "id": "somehex1",
                    "name": "Filter building",
                    "type": "Multiselect",
                    "options": ["apartments", "retail", "house"],
                    "value": ["house"],
                },
            ],
            "raster_layer_data": [],
        }, None

        print(payload)

        self.assertEqual(payload, expected_payload)

    def test_user_script_with_base_and_overlay_layer(self):
        # TODO
        pass


if __name__ == "__main__":
    unittest.main()
